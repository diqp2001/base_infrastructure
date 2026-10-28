"""
Factor value generation for a company-share universe, an interval and a frequency.

Rules
* Eligible factors: CALCULATED factors defined at the requested frequency. A factor is defined per frequency
  (its DependencySpecs follow the parent's frequency); another frequency is refused with the reason, never
  substituted. Raw IBKR series (open / high / low / close / volume ...) are imported by the data preload, not
  generated here.
* Timestamps: the close of every bar of the NYSE calendar in [start, end] (session close for daily factors,
  bar start + bar length intraday). A value stamped t uses only data known at t: the resolution service reads
  CLOSED bars only (FactorValueResolutionService, the same path as every other factor computation).
* Point-in-time universe: a (security, t) is computed only while the security is a constituent at t.
* Idempotent: a value already stored for (factor, security, t) is counted as existing and kept — never
  overwritten (corrections go through the repository's correction path, which invalidates dependents).
* Inputs are read from the database only (no IBKR request from here); a value whose inputs are not stored is
  reported as missing input.

Execution: ``run`` (in-process, used by the worker and the tests) or a background job (``GenerationJobs``): a
separate process, a JSON status file with progress, one job per identical scope at a time.
"""

from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess
import sys
import time
import traceback
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional

import pandas as pd

from src.application.services.research.factor_research import ENTITY_TYPE, bar_minutes_of

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_JOB_ROOT = REPO_ROOT / "results" / "research_jobs"


@dataclass
class GenerationRequest:
    universe_id: int
    start: str
    end: str
    frequency: str
    factor_ids: List[int] = field(default_factory=list)
    all_eligible: bool = False

    def scope_key(self) -> str:
        d = asdict(self)
        d["factor_ids"] = sorted(d["factor_ids"])
        return hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()[:16]


def decision_times(start, end, frequency: str) -> pd.DatetimeIndex:
    """Close of every NYSE bar with start <= bar <= end (naive New York time)."""
    import pandas_market_calendars as mcal
    minutes = bar_minutes_of(frequency)
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    schedule = mcal.get_calendar("NYSE").schedule(start_date=start.normalize(), end_date=end.normalize())
    out = []
    for open_, close in zip(schedule["market_open"], schedule["market_close"]):
        o = pd.Timestamp(open_).tz_convert("America/New_York").tz_localize(None)
        c = pd.Timestamp(close).tz_convert("America/New_York").tz_localize(None)
        if minutes is None:
            out.append(c)
        else:
            step = pd.Timedelta(minutes=minutes)
            out.extend(pd.date_range(o + step, c, freq=step))
    idx = pd.DatetimeIndex(out)
    return idx[(idx >= start) & (idx <= end + pd.Timedelta(days=1) - pd.Timedelta(seconds=1))]


class FactorGenerationService:

    def __init__(self, factory, data=None, resolver=None):
        from src.application.services.research.factor_research import FactorResearchData
        self.factory = factory
        self.data = data or FactorResearchData(factory)
        self._resolver = resolver

    @property
    def resolver(self):
        if self._resolver is None:
            from src.application.services.data.entities.factor.factor_value_resolution_service import (
                FactorValueResolutionService,
            )
            self._resolver = FactorValueResolutionService(factory=self.factory)
        return self._resolver

    def eligible_factors(self, frequency: str) -> List[Dict]:
        return [f for f in self.data.factors() if f["source"] == "calculated" and f["frequency"] == frequency]

    def plan(self, req: GenerationRequest) -> Dict:
        """Validation + what would be computed (no write)."""
        errors, refused = [], {}
        try:
            bar_minutes_of(req.frequency)
        except ValueError as e:
            errors.append(str(e))
        try:
            start, end = pd.Timestamp(req.start), pd.Timestamp(req.end)
            if end < start:
                errors.append("the end is before the start")
        except (ValueError, TypeError):
            errors.append("start and end must be dates or date-times")
            start = end = None
        universes = {u["id"]: u for u in self.data.universes()}
        if req.universe_id not in universes:
            errors.append(f"unknown universe {req.universe_id}")
        defs = {f["id"]: f for f in self.data.factors()}
        eligible = {f["id"] for f in self.eligible_factors(req.frequency)} if not errors else set()
        wanted = sorted(eligible) if req.all_eligible else list(req.factor_ids)
        if not wanted and not errors:
            errors.append("select at least one factor (or all eligible factors)")
        factors = []
        for fid in wanted:
            f = defs.get(fid)
            if f is None:
                refused[fid] = "unknown factor"
            elif f["source"] != "calculated":
                refused[fid] = (f"{f['name']} is a raw {f['source']} series: it is imported (data preload), not "
                                f"generated")
            elif f["frequency"] != req.frequency:
                refused[fid] = (f"{f['name']} is defined at {f['frequency']}, not {req.frequency}: a factor is "
                                f"defined per frequency (its dependencies follow it); choose that factor's frequency "
                                f"or the factor defined at {req.frequency}")
            else:
                factors.append(f)
        if not errors and not factors:
            errors.append("no selected factor can be generated at this frequency (see the reasons)")
        times = decision_times(start, end, req.frequency) if not errors else pd.DatetimeIndex([])
        membership = self.data.membership(req.universe_id) if req.universe_id in universes else []
        cells = 0
        for t in times:
            day = t.normalize()
            cells += sum(1 for _, s, e in membership if pd.Timestamp(s) <= day and (e is None or day < pd.Timestamp(e)))
        return {"errors": errors, "refused": refused, "factors": factors, "timestamps": int(len(times)),
                "first": str(times[0]) if len(times) else None, "last": str(times[-1]) if len(times) else None,
                "constituent_timestamps": cells, "calculations": cells * len(factors),
                "eligible_constituents": len({m[0] for m in membership})}

    def run(self, req: GenerationRequest, progress: Optional[Callable[[Dict], None]] = None,
            should_stop: Optional[Callable[[], bool]] = None) -> Dict:
        plan = self.plan(req)
        if plan["errors"]:
            raise ValueError("; ".join(plan["errors"]))
        started = time.time()
        membership = self.data.membership(req.universe_id)
        times = decision_times(req.start, req.end, req.frequency)
        values_repo = self.factory.factor_value_local_repo
        shares = self.factory.get_local_repository("CompanyShare")
        factor_repo = self.factory.factor_local_repo
        counts = {"generated": 0, "existing": 0, "missing_input": 0, "failed": 0, "updated": 0}
        report: List[Dict] = []
        entities: Dict[int, object] = {}
        done = 0
        stopped = False
        for f in plan["factors"]:
            factor = factor_repo.get_by_id(f["id"])
            for t in times:
                day = t.normalize()
                active = [eid for eid, s, e in membership
                          if pd.Timestamp(s) <= day and (e is None or day < pd.Timestamp(e))]
                for eid in sorted(set(active)):
                    if should_stop is not None and should_stop():
                        stopped = True
                        break
                    stamp = t.strftime("%Y-%m-%d %H:%M:%S")
                    try:
                        if values_repo.get_by_factor_entity_date(int(f["id"]), int(eid), stamp, ENTITY_TYPE):
                            counts["existing"] += 1
                        else:
                            entity = entities.get(eid) or shares.get_by_id(eid)
                            entities[eid] = entity
                            value = self.resolver.resolve_factor_value(factor, entity, t.to_pydatetime())
                            if value is None:
                                counts["missing_input"] += 1
                                if len(report) < 2000:
                                    report.append({"factor": f["name"], "entity_id": eid, "time": stamp,
                                                   "status": "missing input",
                                                   "detail": "a dependency has no stored value known at this time"})
                            else:
                                counts["generated"] += 1
                    except Exception as e:                      # one failure never stops the run
                        counts["failed"] += 1
                        if len(report) < 2000:
                            report.append({"factor": f["name"], "entity_id": eid, "time": stamp, "status": "failed",
                                           "detail": f"{type(e).__name__}: {e}"})
                    done += 1
                    if progress is not None and done % 25 == 0:
                        progress({"done": done, "total": plan["calculations"], **counts})
                if stopped:
                    break
            if stopped:
                break
        summary = {"universe_id": req.universe_id, "factors": [f["name"] for f in plan["factors"]],
                   "refused": plan["refused"], "frequency": req.frequency, "start": req.start, "end": req.end,
                   "timestamps": plan["timestamps"], "eligible_constituents": plan["eligible_constituents"],
                   "calculations": plan["calculations"], "done": done, **counts,
                   "skipped": counts["existing"] + counts["missing_input"],
                   "status": "stopped" if stopped else ("completed_with_errors" if counts["failed"] else "completed"),
                   "duration_seconds": round(time.time() - started, 1), "report": report,
                   "notes": ["Existing values are kept (never overwritten): 'updated' is always 0.",
                             "Inputs are read from the database only; missing inputs are reported, not filled."]}
        if progress is not None:
            progress({"done": done, "total": plan["calculations"], **counts})
        return summary


# ── background jobs ──────────────────────────────────────────────────────────────────────────────────────────────

class GenerationJobs:
    """JSON status files under results/research_jobs/<job id>.json; a worker process per job."""

    def __init__(self, root: Path = DEFAULT_JOB_ROOT, python: str = sys.executable, starter=None, is_alive=None):
        self.root = Path(root)
        self.python = python
        self.starter = starter or self._start
        if is_alive is None:
            from src.application.services.strategy.experiment_service import pid_alive
            is_alive = pid_alive
        self.is_alive = is_alive

    def path(self, job_id: str) -> Path:
        return self.root / f"{job_id}.json"

    def read(self, job_id: str) -> Dict:
        p = self.path(job_id)
        if not p.exists():
            raise LookupError(f"unknown job {job_id}")
        job = json.loads(p.read_text(encoding="utf-8"))
        if job["status"] in ("queued", "running") and not self.is_alive(job.get("pid")) \
                and job.get("host") == socket.gethostname():
            age = time.time() - job.get("updated", job.get("created", 0))
            if job["status"] == "running" or age > 300:
                job.update(status="interrupted", error="the worker process is no longer running")
                self.write(job)
        return job

    def write(self, job: Dict) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        job["updated"] = time.time()
        tmp = self.path(job["id"]).with_suffix(".tmp")
        tmp.write_text(json.dumps(job, default=str), encoding="utf-8")
        os.replace(tmp, self.path(job["id"]))

    def list(self) -> List[Dict]:
        if not self.root.exists():
            return []
        jobs = []
        for p in sorted(self.root.glob("*.json"), reverse=True):
            try:
                jobs.append(self.read(p.stem))
            except (LookupError, ValueError):
                continue
        return jobs

    def launch(self, req: GenerationRequest) -> Dict:
        scope = req.scope_key()
        for job in self.list():
            if job.get("scope") == scope and job["status"] in ("queued", "running"):
                raise RuntimeError(f"job {job['id']} is already generating this scope")
        job_id = f"{datetime.utcnow():%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:6]}"
        job = {"id": job_id, "kind": "factor_generation", "scope": scope, "request": asdict(req), "status": "queued",
               "created": time.time(), "host": socket.gethostname(), "progress": {}, "summary": None, "error": None,
               "log": str(self.root / f"{job_id}.log"), "pid": None}
        self.write(job)
        job["pid"] = self.starter(job)
        self.write(job)
        return job

    def _start(self, job: Dict) -> int:
        self.root.mkdir(parents=True, exist_ok=True)
        log = open(job["log"], "ab")
        flags = (subprocess.CREATE_NEW_PROCESS_GROUP | getattr(subprocess, "CREATE_NO_WINDOW", 0)) if os.name == "nt" else 0
        p = subprocess.Popen([self.python, "-m", "src.application.services.research.factor_generation", job["id"]],
                             cwd=str(REPO_ROOT), stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                             creationflags=flags, close_fds=True)
        log.close()
        return p.pid

    def stop(self, job_id: str) -> None:
        job = self.read(job_id)
        job["stop_requested"] = True
        self.write(job)


def run_job(job_id: str, jobs: GenerationJobs, service: FactorGenerationService) -> Dict:
    job = jobs.read(job_id)
    job.update(status="running", pid=os.getpid(), started=time.time())
    jobs.write(job)

    def progress(p):
        current = jobs.read(job_id)
        current["progress"] = p
        jobs.write(current)

    def should_stop():
        return bool(json.loads(jobs.path(job_id).read_text(encoding="utf-8")).get("stop_requested"))

    try:
        summary = service.run(GenerationRequest(**job["request"]), progress=progress, should_stop=should_stop)
        job = jobs.read(job_id)
        job.update(status=summary["status"], summary=summary, finished=time.time())
    except BaseException as e:
        job = jobs.read(job_id)
        job.update(status="failed", error=f"{type(e).__name__}: {e}\n{traceback.format_exc()[-3000:]}",
                   finished=time.time())
    jobs.write(job)
    return job


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 1:
        print("usage: python -m src.application.services.research.factor_generation <job id>")
        return 2
    from src.application.services.database_service.database_service import DatabaseService
    from src.infrastructure.repositories.repository_factory import RepositoryFactory
    db = DatabaseService("sql_server")
    db.set_ext_db()
    factory = RepositoryFactory(db.session)                    # local repositories only: no IBKR request
    job = run_job(argv[0], GenerationJobs(), FactorGenerationService(factory))
    print(f"job {job['id']}: {job['status']}")
    return 0 if job["status"].startswith("completed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
