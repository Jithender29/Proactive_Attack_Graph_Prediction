"""Live Random Forest detector with a local browser dashboard."""
import argparse
import time
from pathlib import Path
from collections import Counter, defaultdict
import math
from datetime import datetime, timezone
import warnings
from attacker_models import train_model, load_model, predict_session, MODEL_PATH
from pipeline import read_events, event_value, _route_category, monitor_graph_and_sequence
from lstm_model import load_lstm, predict_next
from detector_dashboard import (
    publish_graph_reports,
    publish_sessions,
    set_dashboard_message,
    start_dashboard,
)

IDLE_TIMEOUT_SECONDS = 5 * 60


def _event_datetime(event):
    value = str(event_value(event, "timestamp", default=""))
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def route_entropy(routes):
    counts = Counter(routes); total = sum(counts.values())
    if total == 0: return 0.0
    return -sum((n/total) * math.log2(n/total) for n in counts.values())

def aggregate_sessions(rows, idle_timeout_seconds=IDLE_TIMEOUT_SECONDS):
    groups = defaultdict(list)
    for r in rows:
        actor = event_value(r, "session_fingerprint", "session_id", "ip", "client_ip", default="unknown")
        groups[str(actor)].append(r)
    output = []
    for actor, events in groups.items():
        events.sort(key=lambda event: _event_datetime(event) or datetime.min.replace(tzinfo=timezone.utc))
        sessions = []
        current_events = []
        previous_time = None
        for event in events:
            event_time = _event_datetime(event)
            if (
                current_events
                and event_time is not None
                and previous_time is not None
                and (event_time - previous_time).total_seconds() > idle_timeout_seconds
            ):
                sessions.append(current_events)
                current_events = []
            current_events.append(event)
            if event_time is not None:
                previous_time = event_time
        if current_events:
            sessions.append(current_events)

        for session_index, session_events in enumerate(sessions):
            output.append(_aggregate_session(actor, session_index, session_events))
    return output


def _aggregate_session(actor, session_index, events):
    routes = [str(event_value(r, "route", "path", "endpoint", default="/")) for r in events]
    statuses = [int(event_value(r, "status_code", "status", default=200)) for r in events]
    methods = [str(event_value(r, "method", default="GET")).upper() for r in events]
    features = {
        "requests_per_min": len(events),
        "failed_logins": sum(1 for r, s in zip(routes, statuses) if "login" in r.lower() and s in (401, 403)),
        "not_found_count": sum(s == 404 for s in statuses),
        "client_error_count": sum(400 <= s < 500 for s in statuses),
        "server_error_count": sum(s >= 500 for s in statuses),
        "unique_routes": len(set(routes)),
        "route_entropy": route_entropy(routes),
        "post_ratio": sum(m == "POST" for m in methods) / max(1, len(methods)),
        "admin_requests": sum("/admin" in r.lower() for r in routes),
        "suspicious_pattern_hits": sum(any(x in r.lower() for x in ("../", "union", "select", "<script", "%2e%2e")) for r in routes),
        "burstiness": min(1.0, len(events) / 20.0),
        "distinct_methods": len(set(methods))
    }
    ip = event_value(events[-1], "ip", "client_ip", default="unknown")
    started_at = str(event_value(events[0], "timestamp", default=""))
    last_seen_at = str(event_value(events[-1], "timestamp", default=""))
    first_event_id = event_value(events[0], "id", default=started_at or session_index)
    return {
        "actor": actor,
        "session_id": f"{actor}:{first_event_id}:{session_index}",
        "ip": str(ip),
        "features": features,
        "events": events,
        "started_at": started_at,
        "last_seen_at": last_seen_at,
    }

def session_route_path(events):
    return [
        {
            "route": str(event_value(event, "route", "path", "endpoint", default="/")),
            "method": str(event_value(event, "method", default="GET")).upper(),
            "status": int(event_value(event, "status_code", "status", default=200)),
            "timestamp": str(event_value(event, "timestamp", default="")),
        }
        for event in events
    ]

def detect_policy_alerts(events):
    alerts = []
    for event in events:
        route = str(event_value(event, "route", "path", "endpoint", default="/"))
        admin_path = route.lower().split("?", 1)[0].rstrip("/")
        status = int(event_value(event, "status_code", "status", default=200))
        if (admin_path == "/admin" or admin_path.startswith("/admin/")) and status in (401, 403):
            alert = f"Denied admin request to {route} (HTTP {status})"
            if alert not in alerts:
                alerts.append(alert)
    return alerts

def main():
    warnings.filterwarnings(
        "ignore",
        message=r"`sklearn\.utils\.parallel\.delayed` should be used with `sklearn\.utils\.parallel\.Parallel`",
        category=UserWarning,
        module=r"sklearn\.utils\.parallel",
    )
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="store.db")
    parser.add_argument("--train", action="store_true", help="Train RF then start monitoring")
    parser.add_argument("--poll", type=int, default=5)
    parser.add_argument("--no-graph", action="store_true")
    parser.add_argument("--dashboard-port", type=int, default=8765)
    parser.add_argument(
        "--idle-timeout",
        type=int,
        default=IDLE_TIMEOUT_SECONDS // 60,
        help="Minutes without activity before a session moves to dashboard history",
    )
    args = parser.parse_args()
    if args.idle_timeout < 1:
        parser.error("--idle-timeout must be at least 1 minute")
    if args.train or not Path(MODEL_PATH).exists():
        print("[TRAIN] Training Random Forest model...")
        train_model()
    model = load_model()
    lstm_model = None
    lstm_categories = None
    if not args.no_graph and Path("models/lstm_model.pt").exists():
        lstm_model, lstm_categories, _ = load_lstm()
    dashboard_server, dashboard_url = start_dashboard(port=args.dashboard_port)
    print(f"[DASHBOARD] Live detector interface: {dashboard_url}")
    set_dashboard_message(f"Monitoring {args.db}")
    last_graph_key = None
    try:
        while True:
            rows = read_events(args.db, limit=None)
            dashboard_sessions = []
            history_sessions = []
            sessions_by_actor = {}
            events_by_actor = {}
            session_ids_by_actor = {}
            now = datetime.now(timezone.utc)
            idle_timeout_seconds = args.idle_timeout * 60
            for record in aggregate_sessions(rows, idle_timeout_seconds):
                actor = record["actor"]
                events = record["events"]
                probability, rf_suspicious = predict_session(model, record["features"])
                policy_alerts = detect_policy_alerts(events)
                suspicious = rf_suspicious or bool(policy_alerts)
                last_seen = _event_datetime(events[-1])
                session = {
                    "actor": actor,
                    "session_id": record["session_id"],
                    "ip": record["ip"],
                    "probability": probability,
                    "rf_suspicious": rf_suspicious,
                    "policy_alerts": policy_alerts,
                    "suspicious": suspicious,
                    "features": record["features"],
                    "path": session_route_path(events),
                    "started_at": record["started_at"],
                    "last_seen_at": record["last_seen_at"],
                }
                if lstm_model is not None and lstm_categories is not None:
                    route_sequence = [
                        _route_category(event_value(event, "route", "path", "endpoint", default="/"))
                        for event in events
                    ]
                    next_target, confidence = predict_next(
                        lstm_model,
                        lstm_categories,
                        route_sequence,
                    )
                    session["next_target"] = next_target
                    session["next_confidence"] = confidence
                else:
                    session["next_target"] = None
                    session["next_confidence"] = None
                age_seconds = (now - last_seen).total_seconds() if last_seen else None
                is_live = age_seconds is not None and 0 <= age_seconds <= idle_timeout_seconds
                if is_live:
                    session["is_live"] = True
                    dashboard_sessions.append(session)
                    sessions_by_actor[actor] = session
                    events_by_actor[actor] = events
                    session_ids_by_actor[actor] = record["session_id"]
                else:
                    session["is_live"] = False
                    history_sessions.append(session)
            dashboard_sessions.sort(key=lambda session: session["last_seen_at"], reverse=True)
            history_sessions.sort(key=lambda session: session["last_seen_at"], reverse=True)
            reports = []
            status_message = f"Monitoring {args.db}"
            status_is_error = False
            if not args.no_graph and events_by_actor and Path("models/gnn_model.pt").exists() and Path("models/lstm_model.pt").exists():
                # Run graph/sequence analysis only when the latest event changes.
                latest_event = rows[-1]
                latest = str(event_value(latest_event, "id", default=event_value(latest_event, "timestamp", default="")))
                if latest and latest != last_graph_key:
                    try:
                        active_events = [
                            event
                            for actor_events in events_by_actor.values()
                            for event in actor_events
                        ]
                        reports = monitor_graph_and_sequence(active_events, display=False)
                        for report in reports:
                            report["session_id"] = session_ids_by_actor.get(report["actor"])
                        last_graph_key = latest
                    except Exception as exc:
                        status_message = f"GNN/LSTM inference skipped: {exc}"
                        status_is_error = True
            for report in reports:
                session = sessions_by_actor.get(report["actor"])
                if session:
                    session["graph"] = report
            publish_sessions(dashboard_sessions, history_sessions)
            publish_graph_reports(reports)
            set_dashboard_message(status_message, is_error=status_is_error)
            time.sleep(max(2, args.poll))
    except KeyboardInterrupt:
        set_dashboard_message("Detector stopped.")
    finally:
        dashboard_server.shutdown()
        dashboard_server.server_close()

if __name__ == "__main__":
    main()
