"""
Integrity of pickled model artifacts (BI-015). Unpickling runs code from the file, so an artifact is only loaded
when its SHA-256 matches the one recorded in its ModelArtifact metadata when it was written.

- checksum recorded and different  -> refused (logged), the caller retrains
- no checksum recorded (artifacts written before BI-015) -> loaded with a warning, so existing deployments keep
  working; retraining writes a checksummed artifact
"""

import hashlib
import logging
import os
import pickle
from typing import Any, Optional

logger = logging.getLogger(__name__)


def sha256_of(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_verified_pickle(path: Optional[str], expected_sha256: Optional[str]) -> Optional[Any]:
    """The unpickled object, or None when the file is missing, does not match its checksum or is unreadable."""
    if not path or not os.path.exists(path):
        return None
    actual = sha256_of(path)
    if expected_sha256 and actual != expected_sha256:
        logger.error(f"artifact {path}: SHA-256 {actual[:12]}… differs from the recorded {expected_sha256[:12]}… — "
                     f"not loaded")
        return None
    if not expected_sha256:
        logger.warning(f"artifact {path}: no checksum recorded (written before BI-015) — loaded unverified")
    try:
        with open(path, "rb") as f:
            return pickle.load(f)
    except Exception as e:
        logger.error(f"artifact {path} is unreadable ({type(e).__name__}: {e}) — not used")
        return None
