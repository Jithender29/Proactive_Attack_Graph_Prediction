"""Terminal-only live Random Forest detector for the Mini Amazon events table."""
import argparse
import sqlite3
import time
from pathlib import Path
from collections import Counter, defaultdict
import math
from attacker_models import train_model, load_model, predict_session, DATA_PATH, MODEL_PATH
from pipeline import read_events, event_value, monitor_graph_and_sequence

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

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="store.db")
    parser.add_argument("--train", action="store_true", help="Train RF then start monitoring")
    parser.add_argument("--poll", type=int, default=5)
    parser.add_argument("--no-graph", action="store_true")
    args = parser.parse_args()
    if args.train or not Path(MODEL_PATH).exists():
        print("[TRAIN] Training Random Forest model...")
        train_model()
    model = load_model()
    print(f"[MONITOR] Database={args.db}; terminal-only alerts; Ctrl+C to stop.")
    seen_alerts = set()
    try:
        while True:
            rows = read_events(args.db, limit=2000)
            for actor, ip, feats, events in aggregate_sessions(rows):
                prob, suspicious = predict_session(model, feats)
                last_ts = event_value(events[-1], "timestamp", default="")
                key = (actor, last_ts)
                if suspicious and key not in seen_alerts:
                    seen_alerts.add(key)
                    print("\n" + "!" * 68)
                    print(f"[RANDOM FOREST ALERT] suspicious_probability={prob:.2f}")
                    print(f"Attacker/session identifier: {actor}")
                    print(f"Source IP: {ip}")
                    print(f"Recent route: {event_value(events[-1], 'route', 'path', default='unknown')}")
                    print("Reasons/features:", feats)
                    print("!" * 68)
            if not args.no_graph and rows and Path("models/gnn_model.pt").exists() and Path("models/lstm_model.pt").exists():
                # Run graph/sequence analysis only when the latest event changes.
                latest = str(rows[-1].get("timestamp", ""))
                if latest and latest not in seen_alerts:
                    try:
                        monitor_graph_and_sequence(rows[-300:])
                    except Exception as exc:
                        print(f"[GNN/LSTM] inference skipped: {exc}")
                    seen_alerts.add(latest)
            time.sleep(max(2, args.poll))
    except KeyboardInterrupt:
        print("\n[MONITOR] Stopped by user.")

if __name__ == "__main__":
    main()
