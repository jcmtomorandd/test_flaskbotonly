from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

@app.get("/")
def index():
    # デフォルトトップ画面
    return "<h1>FlaskBotOnly テストサーバー</h1><p>/chat でチャット画面を返します。</p>"

@app.get("/chat")
def chat_window_only():
    # 右下ウィンドウだけを返すルート
    return render_template("test_botonly.html")

@app.post("/api/chat")
def api_chat():
    # ダミー（バックエンド未接続なので、通信テスト用）
    req = request.get_json()
    user_msg = req.get("message", "")
    return jsonify({"message": "（デモ）この返答はバックエンドに未接続です。"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
