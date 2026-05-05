import os
import time
import random
import threading
from flask import Flask, request, jsonify, make_response

app = Flask(__name__)

MODE = os.getenv("MODE", "stable")
VERSION = os.getenv("APP_VERSION", "1.0.0")
PORT = int(os.getenv("APP_PORT", 3000))
START_TIME = time.time()

# Chaos state
chaos_state = {"mode": None, "duration": 0, "rate": 0.0}
chaos_lock = threading.Lock()


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
    return make_resp({"chaos": chaos_state})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
