/* Read-only monitoring dashboard: polls GET endpoints and renders sections. No mutation calls. */
(function () {
  "use strict";

  // ---------------------------------------------------------------- helpers
  function el(tag, attrs, children) {
    const node = document.createElement(tag);
    if (attrs) {
      for (const [k, v] of Object.entries(attrs)) {
        if (v === null || v === undefined || v === false) continue;
        if (k === "class") node.className = v;
        else if (k === "text") node.textContent = v;
        else node.setAttribute(k, v);
      }
    }
    (children || []).forEach(function (c) {
      if (c === null || c === undefined) return;
      node.appendChild(typeof c === "string" || typeof c === "number" ? document.createTextNode(String(c)) : c);
    });
    return node;
  }
  const UNAVAILABLE = function (label) { return el("span", { class: "unavail", text: label || "Unavailable" }); };
  function fmtNum(v, digits) {
    if (v === null || v === undefined || v === "" || Number.isNaN(Number(v))) return null;
    return Number(v).toLocaleString(undefined, { minimumFractionDigits: digits === undefined ? 2 : digits,
                                                 maximumFractionDigits: digits === undefined ? 2 : digits });
  }
  function num(v, digits) { const s = fmtNum(v, digits); return s === null ? UNAVAILABLE() : s; }
  function money(v, cur) {
    const s = fmtNum(v, 2);
    return s === null ? UNAVAILABLE() : s + (cur ? " " + cur : "");
  }
  function text(v, fallback) {
    return v === null || v === undefined || v === "" ? UNAVAILABLE(fallback) : String(v);
  }
  function badge(status) {
    const s = String(status || "unknown").toLowerCase();
    return el("span", { class: "badge s-" + s, text: s });
  }
  function ago(seconds) {
    if (seconds === null || seconds === undefined) return null;
    const s = Math.round(seconds);
    if (s < 60) return s + "s ago";
    if (s < 3600) return Math.round(s / 60) + "m ago";
    if (s < 86400) return Math.round(s / 3600) + "h ago";
    return Math.round(s / 86400) + "d ago";
  }
  function when(iso) {
    if (!iso) return UNAVAILABLE("Never");
    const d = new Date(iso);
    return Number.isNaN(d.getTime()) ? String(iso) : d.toLocaleString();
  }
  function ageOf(iso) {
    if (!iso) return null;
    const d = new Date(iso);
    return Number.isNaN(d.getTime()) ? null : (Date.now() - d.getTime()) / 1000;
  }
  function kv(pairs) {
    const dl = el("dl", { class: "kv" });
    pairs.forEach(function (p) {
      if (!p) return;
      dl.appendChild(el("dt", { text: p[0] }));
      const v = p[1];
      dl.appendChild(el("dd", null, [v === null || v === undefined ? UNAVAILABLE() : v]));
    });
    return dl;
  }
  function table(columns, rows, emptyText) {
    if (!rows || rows.length === 0) return el("div", { class: "empty", text: emptyText || "No rows" });
    const head = el("tr", null, columns.map(function (c) {
      return el("th", { class: c.num ? "num" : null, text: c.label });
    }));
    const body = rows.map(function (r) {
      return el("tr", null, columns.map(function (c) {
        let v = c.render ? c.render(r) : r[c.key];
        if (v === null || v === undefined || v === "") v = UNAVAILABLE(c.missing);
        return el("td", { class: (c.num ? "num " : "") + (c.cls || "") }, [v]);
      }));
    });
    return el("div", { class: "table-wrap" }, [el("table", null, [el("thead", null, [head]), el("tbody", null, body)])]);
  }
  function panel(title, status, children, meta) {
    const head = el("div", { class: "panel-head" }, [el("h2", { text: title }),
      el("div", { class: "right" }, [meta ? el("span", { class: "meta", text: meta }) : null, status ? badge(status) : null])]);
    return el("div", { class: "panel" }, [head].concat(children || []));
  }
  function errorLine(msg) { return msg ? el("div", { class: "error-text", text: msg }) : null; }
  function bool(v) { return v === true ? "Yes" : v === false ? "No" : UNAVAILABLE("Unknown"); }

  // ---------------------------------------------------------------- renderers
  const R = {};

  function statusCard(title, c, valueNode, subText) {
    const head = el("div", { class: "panel-head" }, [el("h2", { text: title }), badge(c.status)]);
    const meta = c.updated_at ? (c.stale ? "STALE - updated " : "updated ") + (ago(c.age_seconds) || "") : "no data yet";
    return el("div", { class: "panel" }, [head,
      el("div", { class: "card-value" }, [valueNode]),
      subText ? el("div", { class: "card-sub", text: subText }) : null,
      el("div", { class: "meta" + (c.stale ? " stale" : ""), text: meta }),
      errorLine(c.error)]);
  }

  R.overview = function (p) {
    const d = p.data;
    const live = d.ibkr && d.ibkr.summary && d.ibkr.summary.mode === "live";
    const out = [];
    if (live) out.push(el("div", { class: "banner live", text: "LIVE trading account connected (monitoring only - no trading from this site)." }));
    const a = d.account.summary;
    out.push(el("div", { class: "grid cols-3" }, [
      statusCard("Application", d.application, text(d.application.summary.version),
                 "uptime " + (ago(d.application.summary.uptime_seconds) || "").replace(" ago", "")),
      statusCard("IB Gateway", d.ibkr, d.ibkr.summary.connected ? "Connected" : "Not connected",
                 (d.ibkr.summary.mode || "?") + " · " + d.ibkr.summary.host + ":" + d.ibkr.summary.port),
      statusCard("SQL Server", d.database, d.database.summary.latency_ms !== undefined && d.database.summary.latency_ms !== null
                 ? fmtNum(d.database.summary.latency_ms, 1) + " ms" : UNAVAILABLE(),
                 (d.database.summary.database || "") + (d.database.summary.read_only_login ? " · read-only login" : "")),
      statusCard("Account data", d.account, a.available ? money(a.net_liquidation, a.currency) : UNAVAILABLE(),
                 "net liquidation"),
      statusCard("Market data", d.market_data, (d.market_data.summary.series || 0) + " series",
                 (d.market_data.summary.stale || 0) + " stale"),
      statusCard("Factors", d.factors, text(fmtNum(d.factors.summary.factor_values, 0)),
                 "factor values · " + d.factors.summary.running_jobs + " running job(s)"),
    ]));
    out.push(panel("Latest errors", d.errors.status, [table([
      { label: "Time", render: function (r) { return when(r.ts); } },
      { label: "Component", key: "component" },
      { label: "Message", key: "message", cls: "msg" },
    ], d.errors.records, "No errors")]));
    return out;
  };

  R.ibkr_connection = function (p) {
    const d = p.data || {};
    const out = [];
    if (d.detected_mode === "live" || d.configured_mode === "live")
      out.push(el("div", { class: "banner live", text: "LIVE account - this dashboard is read-only and cannot trade." }));
    out.push(kv([
      ["Connected", bool(d.connected)],
      ["Endpoint", d.host ? d.host + ":" + d.port : null],
      ["Client id (monitor)", d.client_id !== undefined ? String(d.client_id) : null],
      ["Mode (configured)", text(d.configured_mode)],
      ["Mode (detected)", text(d.detected_mode, "Unknown")],
      ["Accounts", d.accounts && d.accounts.length ? d.accounts.join(", ") : null],
      ["Connected since", when(d.connected_since)],
      ["Last heartbeat", when(d.last_heartbeat)],
      ["Last account update", when(d.last_account_update)],
      ["Last positions update", when(d.last_positions_update)],
      ["Last connection attempt", when(d.last_connect_attempt)],
      d.mode_mismatch ? ["Warning", el("span", { class: "error-text", text: "configured and detected modes differ" })] : null,
    ]));
    out.push(errorLine(p.error));
    if (d.recent_errors && d.recent_errors.length)
      out.push(el("h2", { class: "sub-h", text: "Recent API errors" }),
               table([{ label: "Time", render: function (r) { return when(r.ts); } }, { label: "Code", key: "code", num: true },
                      { label: "Type", key: "kind" }, { label: "Message", key: "message", cls: "msg" }], d.recent_errors));
    if (d.connection_failures && d.connection_failures.length)
      out.push(el("h2", { class: "sub-h", text: "Connection failures" }),
               table([{ label: "Time", render: function (r) { return when(r.ts); } }, { label: "Message", key: "message", cls: "msg" }],
                     d.connection_failures));
    return out;
  };

  R.account_summary = function (p) {
    const d = p.data;
    if (!d) return [el("div", { class: "empty", text: p.error || "Unavailable" })];
    const v = d.values || {};
    function f(label, key) { const x = v[key] || {}; return [label, x.available ? money(x.value, x.currency) : UNAVAILABLE()]; }
    const out = [kv([
      ["Accounts", d.accounts && d.accounts.length ? d.accounts.join(", ") : null],
      ["Account type", text(d.account_type)],
      ["Base currency", text(d.base_currency)],
      f("Net liquidation", "net_liquidation"), f("Total cash", "total_cash_value"), f("Settled cash", "settled_cash"),
      f("Available funds", "available_funds"), f("Excess liquidity", "excess_liquidity"), f("Buying power", "buying_power"),
      f("Equity with loan", "equity_with_loan"), f("Gross position value", "gross_position_value"),
      f("Unrealized P&L", "unrealized_pnl"), f("Realized P&L", "realized_pnl"),
      f("Initial margin", "init_margin"), f("Maintenance margin", "maint_margin"),
    ])];
    out.push(el("h2", { class: "sub-h", text: "Cash by currency" }));
    out.push(table([{ label: "Currency", key: "currency" },
      { label: "Cash balance", num: true, render: function (r) { return money(r.cash_balance, r.currency); } },
      { label: "Net liquidation", num: true, render: function (r) { return money(r.net_liquidation, r.currency); } },
      { label: "Unrealized P&L", num: true, render: function (r) { return money(r.unrealized_pnl, r.currency); } },
      { label: "Realized P&L", num: true, render: function (r) { return money(r.realized_pnl, r.currency); } },
      { label: "FX rate", num: true, render: function (r) { return num(r.exchange_rate, 4); } }], d.cash_by_currency, "Unavailable"));
    out.push(el("h2", { class: "sub-h", text: "Exposure by currency" }));
    out.push(table([{ label: "Currency", key: "currency" },
      { label: "Gross", num: true, render: function (r) { return money(r.gross, r.currency); } },
      { label: "Net", num: true, render: function (r) { return money(r.net, r.currency); } },
      { label: "Positions", key: "positions", num: true }], d.exposure_by_currency, "No priced positions"));
    out.push(el("div", { class: "note", text: d.exposure_note }));
    return out;
  };

  function instrument(r) {
    return [r.symbol, r.local_symbol && r.local_symbol !== r.symbol ? "(" + r.local_symbol + ")" : null,
            r.expiry, r.strike ? r.strike : null, r.right].filter(Boolean).join(" ");
  }

  R.positions = function (p) {
    const d = p.data;
    if (!d) return [el("div", { class: "empty", text: p.error || "Unavailable" })];
    return [table([
      { label: "Instrument", render: instrument }, { label: "Type", key: "sec_type" },
      { label: "Quantity", num: true, render: function (r) { return num(r.quantity, 0); } },
      { label: "Avg cost", num: true, render: function (r) { return money(r.average_cost, r.currency); } },
      { label: "Market price", num: true, render: function (r) { return money(r.market_price, r.currency); } },
      { label: "Market value", num: true, render: function (r) { return money(r.market_value, r.currency); } },
      { label: "Unrealized P&L", num: true, render: function (r) { return money(r.unrealized_pnl, r.currency); } },
      { label: "Currency", key: "currency" }, { label: "Account", key: "account" },
    ], d.positions, "No open positions")];
  };

  R.orders = function (p) {
    const d = p.data;
    if (!d) return [el("div", { class: "empty", text: p.error || "Unavailable" })];
    return [table([
      { label: "Instrument", render: instrument }, { label: "Order id", key: "order_id", num: true },
      { label: "Type", key: "order_type" }, { label: "Side", key: "side" },
      { label: "Quantity", num: true, render: function (r) { return num(r.quantity, 0); } },
      { label: "Filled", num: true, render: function (r) { return num(r.filled, 0); } },
      { label: "Remaining", num: true, render: function (r) { return num(r.remaining, 0); } },
      { label: "Limit", num: true, render: function (r) { return r.limit_price ? money(r.limit_price, r.currency) : null; }, missing: "-" },
      { label: "Status", render: function (r) { return r.status ? badge(String(r.status).toLowerCase()) : null; } },
      { label: "Submitted", render: function (r) { return r.submitted_at ? when(r.submitted_at) : null; }, missing: "Unavailable" },
    ], d.orders, "No open orders"), el("div", { class: "note", text: "Monitoring view only - orders cannot be changed from this site." })];
  };

  R.connections = function (p) {
    const d = p.data;
    const app = d.application.data, db = d.database.data || {}, ib = d.ibkr.data || {};
    const net = (d.network.data || {});
    const probeRows = Object.keys(net).map(function (k) { return Object.assign({ service: k }, net[k]); });
    return [el("div", { class: "grid" }, [
      panel("Python application (dashboard process)", d.application.status, [kv([
        ["Environment", app.environment], ["Version", app.version], ["Python", app.python], ["PID", String(app.pid)],
        ["Started", when(app.started_at)], ["DB collector running", bool(app.collectors.database)],
        ["IBKR collector running", bool(app.collectors.ibkr)], ["Last collection", when(app.last_collection)]])]),
      panel("Flask", d.flask.status, [el("div", { class: "card-sub", text: d.flask.detail })]),
      panel("SQL Server (application level)", d.database.status, [kv([
        ["Database", text(db.database)], ["Query latency", db.latency_ms !== undefined ? fmtNum(db.latency_ms, 1) + " ms" : null],
        ["Server version", text(db.server_version)], ["Edition", text(db.edition)], ["Tables", num(db.table_count, 0)],
        ["Read-only login (SQL Server enforced)", bool(db.db_level_read_only)],
        ["Application read-only guard", bool(db.app_level_read_only_guard)],
        ["Last successful query", when(d.database.last_success)]]), errorLine(d.database.error)]),
      panel("IB Gateway (API level)", d.ibkr.status, [kv([
        ["API connected", bool(ib.connected)], ["Endpoint", ib.host ? ib.host + ":" + ib.port : null],
        ["Last heartbeat", when(ib.last_heartbeat)], ["Mode", text(ib.detected_mode || ib.configured_mode)]]),
        errorLine(d.ibkr.error)]),
    ]),
    panel("Network reachability (container / port level)", d.network.status, [table([
      { label: "Service", key: "service" }, { label: "Host", key: "host" }, { label: "Port", key: "port", num: true },
      { label: "Reachable", render: function (r) { return bool(r.reachable); } },
      { label: "Latency", num: true, render: function (r) { return r.latency_ms !== null && r.latency_ms !== undefined ? fmtNum(r.latency_ms, 1) + " ms" : null; } },
      { label: "Error", key: "error", missing: "-" }], probeRows),
      el("div", { class: "note", text: "A reachable port only means the container accepts TCP; application readiness is shown above." })]),
    panel("Containers", d.containers.status, [el("div", { class: "card-sub", text: d.containers.detail })]),
    panel("Recent connection failures", null, [table([
      { label: "Time", render: function (r) { return when(r.ts); } }, { label: "Message", key: "message", cls: "msg" }],
      (ib.connection_failures || []), "None recorded")]),
    ];
  };

  R.market_data = function (p) {
    const d = p.data || {};
    return [kv([
      ["Series tracked", num(d.total_series, 0)], ["Stale series", num(d.stale_series, 0)],
      ["Sources", d.sources && d.sources.length ? d.sources.map(function (s) { return s.source + " (" + s.factor_count + ")"; }).join(", ") : null],
      ["Last historical retrieval", d.last_historical_retrieval ? when(d.last_historical_retrieval) : UNAVAILABLE()],
      ["Last live update", d.last_live_update ? when(d.last_live_update) : UNAVAILABLE()],
    ]), el("div", { class: "note", text: [d.last_historical_retrieval_note, d.last_live_update_note].filter(Boolean).join(" ") }),
    errorLine(p.error),
    el("h2", { class: "sub-h", text: "Latest observation by series (stalest first)" }),
    table([{ label: "Instrument", render: function (r) { return r.symbol || (r.entity_type + "#" + r.entity_id); } },
      { label: "Factor", key: "factor" }, { label: "Source", key: "source" }, { label: "Frequency", key: "frequency" },
      { label: "Latest", render: function (r) { return when(r.last_timestamp); } },
      { label: "Age", render: function (r) { return ago(r.age_seconds); } },
      { label: "Values", key: "value_count", num: true },
      { label: "State", render: function (r) { return badge(r.state); } }], d.rows, "No market-data series in the database"),
    el("h2", { class: "sub-h", text: "Recent market-data errors" }),
    table([{ label: "Time", render: function (r) { return when(r.ts); } }, { label: "Level", key: "level" },
           { label: "Message", key: "message", cls: "msg" }], d.recent_errors, "None")];
  };

  R.factors = function (p) {
    const d = p.data || {};
    const c = d.counts || {};
    return [kv([
      ["Factors", num(c.factors, 0)], ["Factor values", num(c.factor_values, 0)], ["Financial assets", num(c.financial_assets, 0)],
      ["Calculated factors (listed)", num(d.calculated_factors, 0)],
      ["Running jobs", num((d.running_jobs || []).length, 0)],
      ["Last successful job", d.last_success ? (d.last_success.name + " · " + new Date(d.last_success.finished_at || d.last_success.updated_at).toLocaleString()) : null],
      ["Last failed job", d.last_failure ? (d.last_failure.name + " · " + (d.last_failure.error || "")) : "None"],
    ]), errorLine(p.error),
    el("h2", { class: "sub-h", text: "Factors (most recent values first)" }),
    table([{ label: "Factor", key: "name" }, { label: "Group", key: "group" }, { label: "Source", key: "source" },
      { label: "Frequency", key: "frequency" }, { label: "Values", key: "value_count", num: true },
      { label: "Entities", key: "entity_count", num: true },
      { label: "First", render: function (r) { return r.first_date ? when(r.first_date) : null; }, missing: "-" },
      { label: "Latest", render: function (r) { return r.last_date ? when(r.last_date) : null; }, missing: "No values" },
      { label: "Age", render: function (r) { return ago(r.age_seconds); }, missing: "-" }], d.factors, "No factors defined"),
    el("h2", { class: "sub-h", text: "Recent factor errors" }),
    table([{ label: "Time", render: function (r) { return when(r.ts); } }, { label: "Level", key: "level" },
           { label: "Message", key: "message", cls: "msg" }], d.recent_errors, "None")];
  };

  R.jobs = function (p) {
    const d = p.data || {};
    return [table([{ label: "Job", key: "name" }, { label: "Kind", key: "kind" },
      { label: "Status", render: function (r) { return badge(r.status); } },
      { label: "Started", render: function (r) { return r.started_at ? when(r.started_at) : null; } },
      { label: "Finished", render: function (r) { return r.finished_at ? when(r.finished_at) : null; }, missing: "-" },
      { label: "Duration", num: true, render: function (r) { return r.duration_seconds !== null && r.duration_seconds !== undefined ? fmtNum(r.duration_seconds, 1) + " s" : null; }, missing: "-" },
      { label: "Progress", render: function (r) { return r.details && r.details.percent !== undefined ? fmtNum(r.details.percent, 1) + " %" : null; }, missing: "-" },
      { label: "Error", key: "error", cls: "msg", missing: "-" }], d.jobs, "No jobs recorded yet")];
  };

  R.logs = function (p) {
    const d = p.data || {};
    return [table([{ label: "Time", render: function (r) { return when(r.ts); } },
      { label: "Level", render: function (r) { return el("span", { class: "lvl-" + r.level, text: r.level }); } },
      { label: "Message", key: "message", cls: "msg" },
      { label: "Component", key: "component" }, { label: "Process", key: "process" }], d.records, "No log records match"),
      el("div", { class: "note", text: "Sources: " + ((d.sources || []).map(function (s) { return s.file; }).join(", ") || "dashboard process only") })];
  };

  R.settings = function (p) {
    const d = p.data || {};
    const iv = d.intervals || {};
    return [kv([
      ["Environment", text(d.environment)], ["Version", text(d.version)],
      ["Trading mode (configured)", text(d.ibkr_account_mode)], ["Live trading allowed in app", bool(d.ibkr_allow_live)],
      ["IBKR monitoring", bool(d.ibkr_enabled)], ["IB Gateway endpoint", d.ibkr_host + ":" + d.ibkr_port],
      ["Monitor client id", String(d.ibkr_client_id)],
      ["SQL Server", d.db_host ? d.db_host + ":" + d.db_port + " / " + d.db_name : null],
      ["Read-only database login", bool(d.db_level_read_only)],
      ["Refresh (health / account / positions / data / logs)", [iv.health, iv.account, iv.positions, iv.data, iv.logs].join(" / ") + " s"],
      ["Dashboard", d.dashboard ? d.dashboard.read_only ? "read-only, " + d.dashboard.authentication : "" : null],
    ]), el("div", { class: "note", text: "Configuration is read-only here. Change it in .env and restart the service." })];
  };

  // ---------------------------------------------------------------- section loading
  function sectionParams(section) {
    const params = new URLSearchParams();
    const group = section.getAttribute("data-filters");
    if (group) {
      document.querySelectorAll('[data-filter-group="' + group + '"] [data-param]').forEach(function (input) {
        if (input.value) params.set(input.getAttribute("data-param"), input.value);
      });
    }
    const s = params.toString();
    return s ? "?" + s : "";
  }

  function setMeta(section, payload, failed) {
    const badgeSlot = section.querySelector('[data-role="badge"]');
    const meta = section.querySelector('[data-role="meta"]');
    if (badgeSlot) { badgeSlot.innerHTML = ""; badgeSlot.appendChild(badge(failed ? "error" : payload.status)); }
    if (meta) {
      if (failed) { meta.textContent = "request failed - " + failed; meta.className = "meta stale"; return; }
      const stale = payload.stale;
      const updated = payload.updated_at ? ago(ageOf(payload.updated_at)) : null;
      meta.textContent = (stale ? "STALE · " : "") + (updated ? "updated " + updated : "no data yet");
      meta.className = "meta" + (stale ? " stale" : "");
    }
  }

  function load(section) {
    const body = section.querySelector('[data-role="body"]');
    const url = section.getAttribute("data-endpoint") + sectionParams(section);
    return fetch(url, { method: "GET", headers: { Accept: "application/json" }, cache: "no-store", credentials: "omit" })
      .then(function (r) { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); })
      .then(function (payload) {
        setMeta(section, payload, null);
        const render = R[section.getAttribute("data-render")];
        const nodes = render(payload);
        body.innerHTML = "";
        (Array.isArray(nodes) ? nodes : [nodes]).forEach(function (n) { if (n) body.appendChild(n); });
      })
      .catch(function (err) {
        setMeta(section, null, err.message || "error");
        if (!body.querySelector(".error-text")) body.insertBefore(el("div", { class: "error-text", text: "Could not load this section: " + (err.message || err) }), body.firstChild);
      });
  }

  function schedule(section) {
    const interval = Math.max(2, parseInt(section.getAttribute("data-interval") || "15", 10)) * 1000;
    const tick = function () {
      if (!document.hidden) load(section);
      section._timer = setTimeout(tick, interval);
    };
    section._timer = setTimeout(tick, interval);
  }

  document.addEventListener("DOMContentLoaded", function () {
    const sections = document.querySelectorAll("[data-endpoint]");
    sections.forEach(function (section) {
      load(section);
      schedule(section);
      const btn = section.querySelector('[data-role="refresh"]');
      if (btn) btn.addEventListener("click", function () { load(section); });
    });
    document.querySelectorAll("[data-filter-group] [data-param]").forEach(function (input) {
      const group = input.closest("[data-filter-group]").getAttribute("data-filter-group");
      const evt = input.tagName === "INPUT" ? "input" : "change";
      let debounce;
      input.addEventListener(evt, function () {
        clearTimeout(debounce);
        debounce = setTimeout(function () {
          document.querySelectorAll('[data-filters="' + group + '"]').forEach(load);
        }, 300);
      });
    });
    document.addEventListener("visibilitychange", function () {
      if (!document.hidden) sections.forEach(load);
    });
  });
})();
