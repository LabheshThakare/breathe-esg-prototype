import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const localVitePorts = new Set(["5173", "5174", "5175"]);
const defaultApiBase = localVitePorts.has(window.location.port)
  ? "http://127.0.0.1:8000/api"
  : `${window.location.origin}/api`;
const API_BASE = import.meta.env.VITE_API_BASE_URL || defaultApiBase;

const sourceLabels = {
  sap: "SAP",
  utility: "Utility",
  travel: "Travel",
};

const scopeLabels = {
  scope_1: "Scope 1",
  scope_2: "Scope 2",
  scope_3: "Scope 3",
};

const statusLabels = {
  pending: "Pending",
  approved: "Approved",
  rejected: "Rejected",
  locked: "Locked",
};

function App() {
  const [dashboard, setDashboard] = useState(null);
  const [activities, setActivities] = useState([]);
  const [failedRecords, setFailedRecords] = useState([]);
  const [runs, setRuns] = useState([]);
  const [filters, setFilters] = useState({
    source_type: "",
    scope: "",
    review_status: "",
    flag: "",
  });
  const [selectedActivity, setSelectedActivity] = useState(null);
  const [activeView, setActiveView] = useState("activities");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadAll() {
    setLoading(true);
    setError("");
    try {
      const [dashboardData, activityData, failedData, runData] = await Promise.all([
        apiGet("/dashboard/"),
        apiGet(`/activities/${queryString(filters)}`),
        apiGet("/failed-records/"),
        apiGet("/runs/"),
      ]);
      setDashboard(dashboardData);
      setActivities(activityData.results);
      setFailedRecords(failedData.results);
      setRuns(runData.results);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAll();
  }, [filters.source_type, filters.scope, filters.review_status, filters.flag]);

  const flagOptions = useMemo(() => dashboard?.quality_flags || [], [dashboard]);

  async function openActivity(activityId) {
    try {
      setSelectedActivity(await apiGet(`/activities/${activityId}/`));
    } catch (err) {
      setError(err.message);
    }
  }

  async function review(activityId, action) {
    try {
      await apiPost(`/activities/${activityId}/${action}/`, { actor: "Demo Analyst" });
      const detail = await apiGet(`/activities/${activityId}/`);
      setSelectedActivity(detail);
      await loadAll();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Breathe ESG</p>
          <h1>Analyst Review</h1>
        </div>
        <button className="secondary-button" onClick={loadAll}>Refresh</button>
      </header>

      {error && <div className="error-banner">{error}</div>}

      <section className="summary-grid">
        <Metric label="Raw rows" value={dashboard?.totals.raw_records} />
        <Metric label="Normalized" value={dashboard?.totals.normalized_activities} />
        <Metric label="Failed" value={dashboard?.totals.failed_raw_records} tone="danger" />
        <Metric label="Flagged" value={dashboard?.totals.flagged_activities} tone="warn" />
        <Metric label="CO2e kg" value={formatNumber(dashboard?.totals.co2e_kg)} />
      </section>

      <section className="work-area">
        <div className="toolbar">
          <div className="tabs">
            <button className={activeView === "activities" ? "active" : ""} onClick={() => setActiveView("activities")}>
              Activities
            </button>
            <button className={activeView === "failed" ? "active" : ""} onClick={() => setActiveView("failed")}>
              Failed Rows
            </button>
            <button className={activeView === "runs" ? "active" : ""} onClick={() => setActiveView("runs")}>
              Runs
            </button>
          </div>

          {activeView === "activities" && (
            <div className="filters">
              <Select label="Source" value={filters.source_type} onChange={(source_type) => setFilters({ ...filters, source_type })}>
                <option value="">All sources</option>
                <option value="sap">SAP</option>
                <option value="utility">Utility</option>
                <option value="travel">Travel</option>
              </Select>
              <Select label="Scope" value={filters.scope} onChange={(scope) => setFilters({ ...filters, scope })}>
                <option value="">All scopes</option>
                <option value="scope_1">Scope 1</option>
                <option value="scope_2">Scope 2</option>
                <option value="scope_3">Scope 3</option>
              </Select>
              <Select label="Status" value={filters.review_status} onChange={(review_status) => setFilters({ ...filters, review_status })}>
                <option value="">All statuses</option>
                <option value="pending">Pending</option>
                <option value="approved">Approved</option>
                <option value="rejected">Rejected</option>
                <option value="locked">Locked</option>
              </Select>
              <Select label="Flag" value={filters.flag} onChange={(flag) => setFilters({ ...filters, flag })}>
                <option value="">All flags</option>
                {flagOptions.map((item) => (
                  <option key={item.flag} value={item.flag}>{item.flag}</option>
                ))}
              </Select>
            </div>
          )}
        </div>

        {loading ? (
          <div className="empty-state">Loading review data</div>
        ) : (
          <>
            {activeView === "activities" && (
              <ActivityTable
                activities={activities}
                selectedId={selectedActivity?.id}
                onOpen={openActivity}
                onReview={review}
              />
            )}
            {activeView === "failed" && <FailedTable records={failedRecords} />}
            {activeView === "runs" && <RunsTable runs={runs} />}
          </>
        )}
      </section>

      {selectedActivity && (
        <ActivityDrawer
          activity={selectedActivity}
          onClose={() => setSelectedActivity(null)}
          onReview={review}
        />
      )}
    </main>
  );
}

function Metric({ label, value, tone = "" }) {
  return (
    <article className={`metric ${tone}`}>
      <span>{label}</span>
      <strong>{value ?? "..."}</strong>
    </article>
  );
}

function Select({ label, value, onChange, children }) {
  return (
    <label className="select-wrap">
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {children}
      </select>
    </label>
  );
}

function ActivityTable({ activities, selectedId, onOpen, onReview }) {
  if (!activities.length) return <div className="empty-state">No activities match the current filters</div>;

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Source</th>
            <th>Scope</th>
            <th>Facility</th>
            <th>Activity</th>
            <th>Quantity</th>
            <th>CO2e kg</th>
            <th>Flags</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {activities.map((activity) => (
            <tr key={activity.id} className={selectedId === activity.id ? "selected-row" : ""} onClick={() => onOpen(activity.id)}>
              <td>{sourceLabels[activity.source_type] || activity.source_type}</td>
              <td>{scopeLabels[activity.scope] || activity.scope}</td>
              <td>{activity.facility?.facility_code || "Unmapped"}</td>
              <td>
                <div className="strong-cell">{activity.description}</div>
                <span className="muted">{activity.supplier}</span>
              </td>
              <td>{activity.normalized_value} {activity.normalized_unit}</td>
              <td>{formatNumber(activity.co2e_kg)}</td>
              <td><Flags flags={activity.quality_flags} /></td>
              <td><Status status={activity.review_status} /></td>
              <td>
                <div className="row-actions" onClick={(event) => event.stopPropagation()}>
                  <button onClick={() => onReview(activity.id, "approve")} disabled={activity.review_status === "locked"}>Approve</button>
                  <button onClick={() => onReview(activity.id, "reject")} disabled={activity.review_status === "locked"}>Reject</button>
                  <button onClick={() => onReview(activity.id, "lock")} disabled={activity.review_status !== "approved"}>Lock</button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function FailedTable({ records }) {
  if (!records.length) return <div className="empty-state">No failed rows</div>;

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Source</th>
            <th>Row ID</th>
            <th>Errors</th>
            <th>Payload</th>
          </tr>
        </thead>
        <tbody>
          {records.map((record) => (
            <tr key={record.id}>
              <td>{sourceLabels[record.source_type] || record.source_type}</td>
              <td>{record.source_row_id}</td>
              <td><Flags flags={record.validation_errors} tone="danger" /></td>
              <td><code>{compactJson(record.payload)}</code></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RunsTable({ runs }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Source</th>
            <th>File</th>
            <th>Status</th>
            <th>Total</th>
            <th>Normalized</th>
            <th>Failed</th>
            <th>Completed</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr key={run.id}>
              <td>{sourceLabels[run.source_type] || run.source_type}</td>
              <td>{run.original_filename}</td>
              <td><Status status={run.status} /></td>
              <td>{run.total_rows}</td>
              <td>{run.succeeded_rows}</td>
              <td>{run.failed_rows}</td>
              <td>{formatDate(run.completed_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ActivityDrawer({ activity, onClose, onReview }) {
  return (
    <aside className="drawer" aria-label="Activity detail">
      <div className="drawer-header">
        <div>
          <p className="eyebrow">{sourceLabels[activity.source_type] || activity.source_type}</p>
          <h2>{activity.description}</h2>
        </div>
        <button className="icon-button" onClick={onClose} aria-label="Close detail">×</button>
      </div>

      <div className="drawer-actions">
        <button onClick={() => onReview(activity.id, "approve")} disabled={activity.review_status === "locked"}>Approve</button>
        <button onClick={() => onReview(activity.id, "reject")} disabled={activity.review_status === "locked"}>Reject</button>
        <button onClick={() => onReview(activity.id, "lock")} disabled={activity.review_status !== "approved"}>Lock</button>
      </div>

      <dl className="detail-grid">
        <div><dt>Status</dt><dd><Status status={activity.review_status} /></dd></div>
        <div><dt>Scope</dt><dd>{scopeLabels[activity.scope] || activity.scope}</dd></div>
        <div><dt>Facility</dt><dd>{activity.facility?.name || "Unmapped"}</dd></div>
        <div><dt>CO2e</dt><dd>{formatNumber(activity.co2e_kg)} kg</dd></div>
        <div><dt>Quantity</dt><dd>{activity.normalized_value} {activity.normalized_unit}</dd></div>
        <div><dt>Factor</dt><dd>{activity.emission_factor_key || "None"}</dd></div>
      </dl>

      <section className="drawer-section">
        <h3>Flags</h3>
        <Flags flags={activity.quality_flags} />
      </section>

      <section className="drawer-section">
        <h3>Raw Payload</h3>
        <pre>{JSON.stringify(activity.raw_record?.payload || activity.source_payload, null, 2)}</pre>
      </section>

      <section className="drawer-section">
        <h3>Audit Events</h3>
        <div className="audit-list">
          {activity.audit_events.map((event) => (
            <div key={event.id} className="audit-item">
              <strong>{event.event_type}</strong>
              <span>{event.actor}</span>
              <span>{formatDate(event.created_at)}</span>
            </div>
          ))}
        </div>
      </section>
    </aside>
  );
}

function Flags({ flags = [], tone = "" }) {
  if (!flags.length) return <span className="muted">None</span>;
  return (
    <div className="flags">
      {flags.map((flag) => <span className={`flag ${tone}`} key={flag}>{flag}</span>)}
    </div>
  );
}

function Status({ status }) {
  return <span className={`status ${status}`}>{statusLabels[status] || status}</span>;
}

function queryString(filters) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value) params.set(key, value);
  });
  const value = params.toString();
  return value ? `?${value}` : "";
}

async function apiGet(path) {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) throw new Error(`GET ${path} failed with ${response.status}`);
  return response.json();
}

async function apiPost(path, payload) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.error || `POST ${path} failed with ${response.status}`);
  }
  return response.json();
}

function formatNumber(value) {
  if (value === null || value === undefined) return "...";
  const number = Number(value);
  return Number.isFinite(number) ? number.toLocaleString(undefined, { maximumFractionDigits: 1 }) : value;
}

function formatDate(value) {
  if (!value) return "";
  return new Date(value).toLocaleString();
}

function compactJson(payload) {
  return JSON.stringify(payload).slice(0, 220);
}

createRoot(document.getElementById("root")).render(<App />);
