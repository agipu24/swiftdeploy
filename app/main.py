import os
import time
import random
import threading
from flask import Flask, request, jsonify, make_response, Response

app = Flask(__name__)

MODE = os.getenv("MODE", "stable")
VERSION = os.getenv("APP_VERSION", "1.0.0")
PORT = int(os.getenv("APP_PORT", 3000))
START_TIME = time.time()

# Chaos state
chaos_state = {"mode": None, "duration": 0, "rate": 0.0}
chaos_lock = threading.Lock()

# Metrics state
metrics_lock = threading.Lock()
request_counts = {}       # (method, path, status) -> count
request_durations = {}    # (method, path) -> list of durations
BUCKETS = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]


def record_metrics(method, path, status, duration):
    key = (method, path, str(status))
    dur_key = (method, path)
    with metrics_lock:
        request_counts[key] = request_counts.get(key, 0) + 1
        if dur_key not in request_durations:
            request_durations[dur_key] = []
        request_durations[dur_key].append(duration)
        # keep only last 1000
        if len(request_durations[dur_key]) > 1000:
            request_durations[dur_key] = request_durations[dur_key][-1000:]


@app.before_request
def start_timer():
    request._start_time = time.time()


@app.after_request
def track_metrics(response):
    duration = time.time() - getattr(request, '_start_time', time.time())
    if request.path != '/metrics':
        record_metrics(request.method, request.path, response.status_code, duration)
    return response


def apply_chaos():
    with chaos_lock:
        mode = chaos_state.get("mode")
        if mode == "slow":
            time.sleep(chaos_state.get("duration", 0))
        elif mode == "error":
            if random.random() < chaos_state.get("rate", 0):
                return True
    return False


def make_resp(data, status=200):
    resp = make_response(jsonify(data), status)
    if MODE == "canary":
        resp.headers["X-Mode"] = "canary"
    return resp


@app.route("/")
def index():
    if apply_chaos():
        return make_resp({"error": "chaos error"}, 500)
    return make_resp({
        "message": f"Welcome! Running in {MODE} mode",
        "mode": MODE,
        "version": VERSION,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    })


@app.route("/healthz")
def healthz():
    return make_resp({
        "status": "ok",
        "mode": MODE,
        "uptime_seconds": int(time.time() - START_TIME)
    })


@app.route("/chaos", methods=["POST"])
def chaos():
    if MODE != "canary":
        return make_resp({"error": "chaos only available in canary mode"}, 403)
    body = request.get_json()
    with chaos_lock:
        m = body.get("mode")
        if m == "slow":
            chaos_state["mode"] = "slow"
            chaos_state["duration"] = body.get("duration", 1)
        elif m == "error":
            chaos_state["mode"] = "error"
            chaos_state["rate"] = body.get("rate", 0.5)
        elif m == "recover":
            chaos_state["mode"] = None
            chaos_state["duration"] = 0
            chaos_state["rate"] = 0.0
    return make_resp({"chaos": chaos_state})


@app.route("/metrics")
def metrics():
    lines = []

    # http_requests_total
    lines.append("# HELP http_requests_total Total HTTP requests")
    lines.append("# TYPE http_requests_total counter")
    with metrics_lock:
        for (method, path, status), count in request_counts.items():
            lines.append(
                f'http_requests_total{{method="{method}",path="{path}",status_code="{status}"}} {count}'
            )

    # http_request_duration_seconds histogram
    lines.append("# HELP http_request_duration_seconds Request duration histogram")
    lines.append("# TYPE http_request_duration_seconds histogram")
    with metrics_lock:
        for (method, path), durations in request_durations.items():
            count = len(durations)
            total = sum(durations)
            for bucket in BUCKETS:
                b_count = sum(1 for d in durations if d <= bucket)
                lines.append(
                    f'http_request_duration_seconds_bucket{{method="{method}",path="{path}",le="{bucket}"}} {b_count}'
                )
            lines.append(
                f'http_request_duration_seconds_bucket{{method="{method}",path="{path}",le="+Inf"}} {count}'
            )
            lines.append(
                f'http_request_duration_seconds_sum{{method="{method}",path="{path}"}} {total:.6f}'
            )
            lines.append(
                f'http_request_duration_seconds_count{{method="{method}",path="{path}"}} {count}'
            )

    # app_uptime_seconds
    lines.append("# HELP app_uptime_seconds App uptime in seconds")
    lines.append("# TYPE app_uptime_seconds gauge")
    lines.append(f"app_uptime_seconds {int(time.time() - START_TIME)}")

    # app_mode
    lines.append("# HELP app_mode Current mode (0=stable, 1=canary)")
    lines.append("# TYPE app_mode gauge")
    lines.append(f"app_mode {1 if MODE == 'canary' else 0}")

    # chaos_active
    lines.append("# HELP chaos_active Chaos state (0=none, 1=slow, 2=error)")
    lines.append("# TYPE chaos_active gauge")
    with chaos_lock:
        cm = chaos_state.get("mode")
        cv = 0 if cm is None else (1 if cm == "slow" else 2)
    lines.append(f"chaos_active {cv}")

    return Response("\n".join(lines) + "\n", mimetype="text/plain")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
