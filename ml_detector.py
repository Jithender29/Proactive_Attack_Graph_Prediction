"""Live Random Forest detector with a local browser dashboard."""
import argparse
import time
from pathlib import Path
from collections import Counter, defaultdict
import math
from attacker_models import train_model, load_model, predict_session, MODEL_PATH
from pipeline import read_events, read_session_events, event_value, monitor_graph_and_sequence
from detector_dashboard import (
    publish_graph_reports,
    publish_sessions,
    set_dashboard_message,
    start_dashboard,
)

def route_entropy(routes):
    counts = Counter(routes); total = sum(counts.values())
    if total == 0: return 0.0
    return -sum((n/total) * math.log2(n/total) for n in counts.values())

def aggregate_sessions(rows):
    groups = defaultdict(list)
    for r in rows:
        actor = event_value(r, "session_fingerprint", "session_id", "ip", "client_ip", default="unknown")
        groups[str(actor)].append(r)
    output = []
    for actor, events in groups.items():
        routes = [str(event_value(r, "route", "path", "endpoint", default="/")) for r in events]
        statuses = [int(event_value(r, "status_code", "status", default=200)) for r in events]
        methods = [str(event_value(r, "method", default="GET")).upper() for r in events]
        timestamps = [str(event_value(r, "timestamp", default="")) for r in events]
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
        output.append((actor, str(ip), features, events))
    return output

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
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="store.db")
    parser.add_argument("--train", action="store_true", help="Train RF then start monitoring")
    parser.add_argument("--poll", type=int, default=5)
    parser.add_argument("--no-graph", action="store_true")
    parser.add_argument("--dashboard-port", type=int, default=8765)
    args = parser.parse_args()
    if args.train or not Path(MODEL_PATH).exists():
        print("[TRAIN] Training Random Forest model...")
        train_model()
    model = load_model()
    dashboard_server, dashboard_url = start_dashboard(port=args.dashboard_port)
    print(f"[DASHBOARD] Live detector interface: {dashboard_url}")
    set_dashboard_message(f"Monitoring {args.db}")
    last_graph_key = None
    full_path_cache = {}

    def full_route_path(actor, events):
        latest = events[-1]
        version = str(event_value(
            latest,
            "id",
            default="{}|{}|{}".format(
                event_value(latest, "timestamp", default=""),
                event_value(latest, "route", "path", default=""),
                event_value(latest, "status_code", "status", default=""),
            ),
        ))
        cached = full_path_cache.get(actor)
        if cached and cached[0] == version:
            return cached[1]
        history = read_session_events(args.db, actor)
        path = session_route_path(history or events)
        full_path_cache[actor] = (version, path)
        return path

    try:
        while True:
            rows = read_events(args.db, limit=2000)
            dashboard_sessions = []
            sessions_by_actor = {}
            events_by_actor = {}
            for actor, ip, feats, events in aggregate_sessions(rows):
                prob, rf_suspicious = predict_session(model, feats)
                policy_alerts = detect_policy_alerts(events)
                suspicious = rf_suspicious or bool(policy_alerts)
                latest_event = events[-1]
                session = {
                    "actor": actor,
                    "ip": ip,
                    "probability": prob,
                    "rf_suspicious": rf_suspicious,
                    "policy_alerts": policy_alerts,
                    "suspicious": suspicious,
                    "features": feats,
                    "path": session_route_path(events),
                }
                if suspicious:
                    session["path"] = full_route_path(actor, events)
                dashboard_sessions.append(session)
                sessions_by_actor[actor] = session
                events_by_actor[actor] = events
            reports = []
            status_message = f"Monitoring {args.db}"
            status_is_error = False
            if not args.no_graph and rows and Path("models/gnn_model.pt").exists() and Path("models/lstm_model.pt").exists():
                # Run graph/sequence analysis only when the latest event changes.
                latest_event = rows[-1]
                latest = str(event_value(latest_event, "id", default=event_value(latest_event, "timestamp", default="")))
                if latest and latest != last_graph_key:
                    try:
                        reports = monitor_graph_and_sequence(rows[-300:], display=False)
                        last_graph_key = latest
                    except Exception as exc:
                        status_message = f"GNN/LSTM inference skipped: {exc}"
                        status_is_error = True
            for report in reports:
                session = sessions_by_actor.get(report["actor"])
                if report["suspicious"] and session:
                    actor_events = events_by_actor[report["actor"]]
                    session["path"] = full_route_path(report["actor"], actor_events)
            publish_sessions(dashboard_sessions)
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
