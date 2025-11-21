from flask import Flask, request, jsonify, render_template
import requests, sys, time

app = Flask(__name__)

# ===== 固定設定（Flask5000 と同じ値） =====
FLOW_ID = "55bf24db-e401-4f1c-a42f-38939d362338"
API_KEY = "sk-YorVRHvFLxg7XhWiVA5PXWQR0m-YPAXgq0qjmCqwIk4"
BASE    = "http://localhost:7870"
# ========================================

@app.get("/")
def index():
    # FlaskBot では Chatbotだけの画面を表示
    return render_template("test_botonly.html")

@app.get("/healthz")
def healthz():
    return jsonify({"status": "ok"})

def _extract_text(d: dict) -> str:
    try_paths = [
        ("outputs", 0, "outputs", 0, "results", "text"),
        ("outputs", 0, "outputs", 0, "results", "message", "text"),
        ("outputs", 0, "outputs", 0, "results", "message", "data", "text"),
        ("text",),
    ]
    for path in try_paths:
        cur = d
        ok = True
        for p in path:
            if isinstance(cur, list):
                if isinstance(p, int):
                    cur = cur[p] if len(cur) > p else None
                else:
                    ok = False
                    break
            elif isinstance(cur, dict):
                if isinstance(p, int):
                    ok = False
                    break
                cur = cur.get(p)
            else:
                ok = False
                break
            if cur is None:
                ok = False
                break
        if ok and isinstance(cur, str) and cur.strip():
            return cur.strip()
    return ""

def call_langflow(message: str, session_id="web"):
    """(ok, text, raw_json, status, elapsed)"""
    url = f"{BASE}/api/v1/run/{FLOW_ID}?stream=false"
    payload = {
        "input_value": message,
        "input_type": "chat",
        "output_type": "chat",
        "session_id": session_id,
    }
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "x-api-key": API_KEY,
        "Authorization": f"Bearer {API_KEY}",
    }
    t0 = time.perf_counter()
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=45)
        elapsed = time.perf_counter() - t0
    except Exception as e:
        return False, f"[通信エラー] {e}", {}, 0, 0.0

    status = r.status_code
    body_text = r.text[:800] if r.text else ""
    try:
        d = r.json()
    except Exception:
        print(
            f"[Langflow RAW] status={status} elapsed={elapsed:.2f}s body~ {body_text!r}",
            file=sys.stdout,
        )
        return False, f"[Langflow応答がJSONでない] status={status}", {}, status, elapsed

    text = _extract_text(d)
    print(
        f"[Langflow] status={status} elapsed={elapsed:.2f}s text~ {text[:120]!r}",
        file=sys.stdout,
    )

    if status >= 400:
        return False, f"[Langflowエラー] {status} {body_text}", d, status, elapsed

    return True, (text if text else "[空の応答]"), d, status, elapsed

@app.post("/api/chat")
def api_chat_post():
    body = request.get_json(silent=True) or {}
    msg = (body.get("message") or body.get("text") or "").strip()
    if not msg:
        return jsonify({"ok": False, "error": "message required"}), 400
    ok, res_text, raw, status, elapsed = call_langflow(msg, session_id="local")
    print(
        f"[/api/chat] ok={ok} status={status} {elapsed:.2f}s msg={msg!r} -> {res_text[:120]!r}",
        file=sys.stdout,
    )
    code = 200 if ok else 502
    return (
        jsonify(
            {
                "ok": ok,
                "reply": res_text,
                "text": res_text,
                "message": res_text,
                "message_obj": {"text": res_text},
            }
        ),
        code,
    )

@app.post("/api/send")
def api_send():
    return api_chat_post()

@app.get("/api/chat")
def api_chat_get():
    msg = (request.args.get("message") or request.args.get("text") or "").strip()
    if not msg:
        return jsonify(
            {"ok": False, "error": "message required (use ?message=hello)"}
        ), 400
    ok, res_text, raw, status, elapsed = call_langflow(msg, session_id="local")
    print(
        f"[/api/chat(GET)] ok={ok} status={status} {elapsed:.2f}s msg={msg!r} -> {res_text[:120]!r}",
        file=sys.stdout,
    )
    code = 200 if ok else 502
    return (
        jsonify(
            {
                "ok": ok,
                "reply": res_text,
                "text": res_text,
                "message": res_text,
                "message_obj": {"text": res_text},
            }
        ),
        code,
    )

@app.route("/api/raw", methods=["GET", "POST"])
def api_raw():
    if request.method == "POST":
        body = request.get_json(silent=True) or {}
        msg = (body.get("message") or body.get("text") or "ping").strip()
    else:
        msg = (request.args.get("message") or request.args.get("text") or "ping").strip()
    ok, res_text, raw, status, elapsed = call_langflow(msg, session_id="debug")
    return (
        jsonify(
            {
                "ok": ok,
                "status": status,
                "elapsed": elapsed,
                "raw": raw,
                "preview": res_text,
            }
        ),
        (200 if ok else 502),
    )

if __name__ == "__main__":
    # FlaskBot は 5002番ポートで動かす（Flask5000 と分ける）
    app.run(host="127.0.0.1", port=5002, debug=True)
