import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock, Thread
from datetime import datetime, timezone
import webbrowser


_DASHBOARD_FILE = Path(__file__).with_name("detector_dashboard.html")
_STATE_LOCK = Lock()
_STATE = {
    "sessions": [],
    "history": [],
    "updated_at": None,
    "message": "Waiting for detector data.",
    "is_error": False,
}


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def publish_sessions(sessions, history=None):
    history = history or []
    with _STATE_LOCK:
        previous = {
            session.get("session_id", session["actor"]): session
            for session in _STATE["sessions"] + _STATE["history"]
        }

        def retain_graph(records):
            current = []
            for session in records:
                record = dict(session)
                key = record.get("session_id", record["actor"])
                record["graph"] = previous.get(key, {}).get("graph")
                current.append(record)
            return current

        _STATE["sessions"] = retain_graph(sessions)
        _STATE["history"] = retain_graph(history)
        _STATE["updated_at"] = _now()


def publish_graph_reports(reports):
    if not reports:
        return
    with _STATE_LOCK:
        for report in reports:
            for session in _STATE["sessions"] + _STATE["history"]:
                matches_session = (
                    report.get("session_id") is not None
                    and session.get("session_id") == report["session_id"]
                )
                matches_actor = (
                    report.get("session_id") is None
                    and session["actor"] == report["actor"]
                )
                if matches_session or matches_actor:
                    session["graph"] = report
        _STATE["updated_at"] = _now()


def set_dashboard_message(message, is_error=False):
    with _STATE_LOCK:
        _STATE["message"] = message
        _STATE["is_error"] = is_error


class _DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            content = _DASHBOARD_FILE.read_bytes()
            content_type = "text/html; charset=utf-8"
        elif self.path == "/api/state":
            with _STATE_LOCK:
                content = json.dumps(_STATE).encode("utf-8")
            content_type = "application/json; charset=utf-8"
        else:
            self.send_error(404)
            return

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format, *args):
        return


def start_dashboard(host="127.0.0.1", port=8765, open_browser=True):
    server = ThreadingHTTPServer((host, port), _DashboardHandler)
    server.daemon_threads = True
    Thread(target=server.serve_forever, daemon=True).start()
    url = "http://{}:{}/".format(host, server.server_port)
    if open_browser:
        webbrowser.open(url)
    return server, url
