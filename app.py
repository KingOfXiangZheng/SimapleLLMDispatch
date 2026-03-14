"""SimapleLLMDispatch — Python Edition."""

import os
from flask import Flask, request, redirect, make_response
from flask_cors import CORS

import config
from database import init_db
from routes.admin import admin_bp
from routes.proxy import proxy_bp


def create_app() -> Flask:
    app = Flask(__name__, static_folder="public/dist", static_url_path="")
    CORS(app)

    init_db()

    app.register_blueprint(admin_bp)
    app.register_blueprint(proxy_bp)

    # Login page template (Glassmorphism)
    LOGIN_HTML = """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>登录 - SimapleLLMDispatch</title>
        <style>
            :root {
                --bg: #0f172a;
                --surface: rgba(30, 41, 59, 0.7);
                --accent: #6366f1;
                --text: #f8fafc;
                --muted: #94a3b8;
            }
            body {
                margin: 0;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
                height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                color: var(--text);
            }
            .login-card {
                background: var(--surface);
                backdrop-filter: blur(12px);
                border: 1px solid rgba(255, 255, 255, 0.1);
                padding: 2.5rem;
                border-radius: 1.5rem;
                width: 360px;
                box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
                text-align: center;
            }
            .brand { font-size: 2rem; margin-bottom: 0.5rem; }
            .title { font-weight: 700; font-size: 1.25rem; margin-bottom: 0.25rem; }
            .sub { color: var(--muted); font-size: 0.875rem; margin-bottom: 2rem; }
            .form-group { text-align: left; margin-bottom: 1.5rem; }
            label { display: block; font-size: 0.875rem; margin-bottom: 0.5rem; color: var(--muted); }
            input {
                width: 100%;
                background: rgba(0, 0, 0, 0.2);
                border: 1px solid rgba(255, 255, 255, 0.1);
                padding: 0.75rem;
                border-radius: 0.5rem;
                color: white;
                box-sizing: border-box;
                outline: none;
                transition: border-color 0.2s;
            }
            input:focus { border-color: var(--accent); }
            button {
                width: 100%;
                background: var(--accent);
                color: white;
                border: none;
                padding: 0.75rem;
                border-radius: 0.5rem;
                font-weight: 600;
                cursor: pointer;
                transition: opacity 0.2s;
            }
            button:hover { opacity: 0.9; }
            button:disabled { opacity: 0.5; cursor: not-allowed; }
            .error { color: #ef4444; font-size: 0.875rem; margin-top: 1rem; display: none; }
        </style>
    </head>
    <body>
        <div class="login-card">
            <div class="brand">⚡</div>
            <div class="title">SimapleLLMDispatch</div>
            <div class="sub">管理面板访问锁定</div>
            <div class="form-group">
                <label>管理密钥 (ADMIN_KEY)</label>
                <input type="password" id="key" placeholder="••••••••" autofocus>
            </div>
            <button id="loginBtn">进入面板</button>
            <div id="errMsg" class="error">密钥错误，请重试</div>
        </div>
        <script>
            const btn = document.getElementById('loginBtn');
            const input = document.getElementById('key');
            const err = document.getElementById('errMsg');

            async function doLogin() {
                const val = input.value;
                if (!val) return;
                btn.disabled = true;
                err.style.display = 'none';

                try {
                    const res = await fetch('/admin/login', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ key: val })
                    });
                    if (res.ok) {
                        const data = await res.json();
                        // Set cookie manually for standard browser behavior
                        document.cookie = `admin_token=${data.token}; path=/; max-age=2592000; SameSite=Strict`;
                        // Also store in localStorage for the SPA's fetch header
                        localStorage.setItem('admin_token', data.token);
                        window.location.reload();
                    } else {
                        err.style.display = 'block';
                    }
                } catch (e) {
                    err.innerText = '连接服务器失败';
                    err.style.display = 'block';
                } finally {
                    btn.disabled = false;
                }
            }

            btn.onclick = doLogin;
            input.onkeyup = (e) => { if (e.key === 'Enter') doLogin(); };
        </script>
    </body>
    </html>
    """

    # Serve dashboard at root
    @app.route("/")
    def index():
        if not config.ADMIN_KEY:
            return app.send_static_file("index.html")
        
        token = request.cookies.get("admin_token")
        if token == config.ADMIN_KEY:
            return app.send_static_file("index.html")
        
        return LOGIN_HTML

    return app


if __name__ == "__main__":
    app = create_app()
    print(f"SimapleLLMDispatch (Python) running at http://localhost:{config.PORT}")
    app.run(host="0.0.0.0", port=config.PORT, debug=os.environ.get("DEBUG", "0") == "1")
