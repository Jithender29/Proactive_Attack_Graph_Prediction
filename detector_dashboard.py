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
    "updated_at": None,
    "message": "Waiting for detector data.",
    "is_error": False,
}


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def publish_sessions(sessions):
    with _STATE_LOCK:
        previous = {session["actor"]: session for session in _STATE["sessions"]}
        current = []
        for session in sessions:
            record = dict(session)
            record["graph"] = previous.get(record["actor"], {}).get("graph")
            current.append(record)
        _STATE["sessions"] = current
        _STATE["updated_at"] = _now()


def publish_graph_reports(reports):
    if not reports:
        return
    with _STATE_LOCK:
        sessions = {session["actor"]: session for session in _STATE["sessions"]}
        for report in reports:
            if report["actor"] in sessions:
                sessions[report["actor"]]["graph"] = report
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
