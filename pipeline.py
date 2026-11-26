"""Training and inference orchestration for GNN + LSTM."""
import argparse
from pathlib import Path
from collections import defaultdict
import numpy as np
from gnn_model import train_gnn, load_gnn, score_graph
from lstm_model import train_lstm, load_lstm, predict_next, CATEGORIES

DB_PATH = Path("store.db")

def _route_category(path):
    p = (path or "/").lower()
    if p.startswith("/admin"): return "admin"
    if p.startswith("/api"): return "api"
    if "login" in p: return "login"
    if "checkout" in p: return "checkout"
    if "cart" in p: return "cart"
    if "order" in p: return "orders"
    if "product" in p or "search" in p: return "products" if "product" in p else "search"
    if p == "/": return "home"
    return "other"

def read_events(db_path=DB_PATH, limit=1000):
    import sqlite3
    if not Path(db_path).exists():
        return []
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    try:
        cols = [r[1] for r in con.execute("PRAGMA table_info(events)").fetchall()]
        if not cols: return []
        if limit is None:
            query = "SELECT * FROM events ORDER BY timestamp ASC"
            params = ()
        else:
            query = "SELECT * FROM events ORDER BY timestamp DESC LIMIT ?"
            params = (limit,)
        rows = con.execute(query, params).fetchall()
        if limit is not None:
            rows.reverse()
        return [dict(r) for r in rows]
    except Exception as exc:
        print(f"[DB] Could not read events table: {exc}")
        return []
    finally:
        con.close()

def read_session_events(db_path, actor):
    import sqlite3
    if not Path(db_path).exists():
        return []
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    try:
        cols = [r[1] for r in con.execute("PRAGMA table_info(events)").fetchall()]
        if not cols: return []
        identity_columns = [
            name for name in ("session_fingerprint", "session_id", "ip", "client_ip")
            if name in cols
        ]
        if identity_columns:
            identity = "COALESCE({}, 'unknown')".format(
                ", ".join("CAST({} AS TEXT)".format(name) for name in identity_columns)
            )
        else:
            identity = "'unknown'"
        query = "SELECT * FROM events WHERE {} = ? ORDER BY timestamp ASC".format(identity)
        rows = con.execute(query, (str(actor),)).fetchall()
        return [dict(row) for row in rows]
    except Exception as exc:
        print(f"[DB] Could not read session events: {exc}")
        return []
    finally:
        con.close()

def event_value(row, *names, default=None):
    for name in names:
        if name in row and row[name] is not None:
            return row[name]
    return default

def train_all():
    print("\n========== TRAIN GNN =========="); train_gnn()
    print("\n========== TRAIN LSTM ========="); train_lstm()
    print("\n[OK] GNN and LSTM training complete.")

def monitor_graph_and_sequence(rows, display=True):
    if not rows: return []
    gnn = load_gnn()
    lstm, categories, seq_len = load_lstm()
    reports = []
    # Group recent event records by session fingerprint, falling back to IP.
    groups = defaultdict(list)
    for r in rows:
        key = event_value(r, "session_fingerprint", "session_id", "ip", "client_ip", default="unknown")
        groups[str(key)].append(r)
    for actor, events in groups.items():
        events = events[-30:]
        if not events: continue
        x = []
        routes = []
        for r in events:
            path = event_value(r, "route", "path", "endpoint", default="/")
            status = int(event_value(r, "status_code", "status", default=200))
            method = str(event_value(r, "method", default="GET")).upper()
            routes.append(_route_category(path))
            x.append([
                min(float(event_value(r, "duration_ms", default=0))/1000, 5),
                float(status == 401), float(status == 404),
                float(400 <= status < 500), float(status >= 500),
                float(str(path).startswith("/admin")),
                float(method == "POST"),
                float(any(s in str(path).lower() for s in ("../", "select", "<script", "union")))
            ])
        n = len(x); adj = np.zeros((n, n), dtype=np.float32)
        for i in range(n-1): adj[i, i+1] = adj[i+1, i] = 1
        scores = score_graph(gnn, np.asarray(x, dtype=np.float32), adj)
        route, confidence = predict_next(lstm, categories, routes)
        max_node_risk = float(scores.max())
        report = {
            "actor": actor,
            "nodes": n,
            "max_node_risk": max_node_risk,
            "next_target": route,
            "confidence": float(confidence),
            "suspicious": max_node_risk >= .65,
        }
        reports.append(report)
        if display:
            print(f"\n[ATTACK GRAPH] actor={actor} nodes={n} max_node_risk={max_node_risk:.2f}")
            print(f"[NEXT TARGET] {route} (model confidence {confidence:.2f})")
            if report["suspicious"]:
                print("[GNN ALERT] Suspicious event chain detected; inspect this session.")
    return reports

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["train-gnn", "train-lstm", "train-all", "monitor"])
    parser.add_argument("--db", default=str(DB_PATH))
    parser.add_argument("--poll", type=int, default=5)
    args = parser.parse_args()
    if args.mode == "train-gnn": train_gnn()
    elif args.mode == "train-lstm": train_lstm()
    elif args.mode == "train-all": train_all()
    else:
        import time
        print(f"[MONITOR] Reading SQLite events from {args.db}; Ctrl+C to stop.")
        seen = set()
        while True:
            rows = read_events(args.db)
            fresh = [r for r in rows if str(r.get("id", (r.get("timestamp"), r.get("route")))) not in seen]
            for r in fresh: seen.add(str(r.get("id", (r.get("timestamp"), r.get("route")))))
            if fresh: monitor_graph_and_sequence(rows)
            time.sleep(max(2, args.poll))

if __name__ == "__main__":
    main()
