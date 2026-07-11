#!/usr/bin/env python3
"""
英语学习应用的本地/云端代理 + 静态服务器（纯标准库，无第三方依赖）。

为什么需要它：
  DeepL 的 API 不允许浏览器跨域（CORS）直连，网页直接 fetch 会被浏览器拦截，
  报 "NetworkError"。本脚本在本地（或云端）起一个同源服务器：网页把翻译请求
  发给它（同源，无 CORS 问题），它再代发到 DeepL 并返回结果。

部署就绪（CloudStudio / 公网）：
  - 监听地址：环境变量 DEEPL_PROXY_HOST（默认 0.0.0.0，即对外可访问）
  - 监听端口：环境变量 PORT 或 DEEPL_PROXY_PORT（默认 8000）
  - Token 保护：设置环境变量 DEEPL_PROXY_TOKEN 后，/__deepl/translate 与
    /__deepl/usage 必须携带正确 Token（请求头 X-Proxy-Token 或参数 token），
    否则返回 401。这样公网部署时别人无法盗用你的 DeepL 额度。
    /__deepl/health 始终开放，供网页自动探测代理是否存在。
  - 服务器端密钥：设置环境变量 DEEPL_API_KEY 后，网页【无需填写】DeepL 密钥即可
    使用（代理自动用该密钥）。适合公开部署时统一托管密钥，用户只需填代理 Token；
    健康检查会返回 server_has_key 供前端判断。若网页也传了 key，则以网页的为准。

本地用法：
  cd english-learning-app
  python3 deepl_proxy.py            # 默认 http://localhost:8000
  python3 deepl_proxy.py 9000       # 指定端口
  DEEPL_PROXY_TOKEN=xxxx python3 deepl_proxy.py   # 启用 Token 保护

安全说明：
  - 仅转发到 DeepL 官方域名（api-free.deepl.com / api.deepl.com），不接受任意 URL，避免 SSRF。
  - 密钥由浏览器随请求发给本代理，不会外泄给第三方。
"""
import os
import sys
import json
import urllib.request
import urllib.error
from urllib.parse import urlparse, parse_qs
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN = (os.environ.get("DEEPL_PROXY_TOKEN") or "").strip()
SERVER_KEY = (os.environ.get("DEEPL_API_KEY") or "").strip()  # 服务器端托管的 DeepL 密钥（可选）


def deepl_host(key):
    """免费密钥以 :fx 结尾走 api-free；其它走 api.deepl.com。"""
    return "https://api-free.deepl.com" if key.endswith(":fx") else "https://api.deepl.com"


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=DIR, **k)

    def log_message(self, fmt, *args):
        pass  # 静默日志，避免刷屏

    def _send_json(self, code, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self, headers, query, body_obj):
        if not TOKEN:
            return True
        h = headers.get("X-Proxy-Token", "")
        q = query.get("token", [""])[0]
        b = (body_obj or {}).get("token", "")
        return h == TOKEN or q == TOKEN or b == TOKEN

    def _call_deepl(self, method, path, key, data=None):
        url = deepl_host(key) + path
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", "DeepL-Auth-Key " + key)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=25) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def do_GET(self):
        if self.path == "/__deepl/health":
            self._send_json(200, {"ok": True, "token_required": bool(TOKEN), "server_has_key": bool(SERVER_KEY), "note": "DeepL proxy is running"})
            return
        if self.path.startswith("/__deepl/usage"):
            qs = parse_qs(urlparse(self.path).query)
            key = (qs.get("key", [""])[0] or "").strip() or SERVER_KEY
            if not key:
                self._send_json(400, {"error": "missing key"})
                return
            if not self._authorized(self.headers, qs, None):
                self._send_json(401, {"error": "unauthorized: proxy token required"})
                return
            try:
                data = self._call_deepl("GET", "/v2/usage", key)
                self._send_json(200, data)
            except urllib.error.HTTPError as e:
                self._send_json(e.code, self._safe_err(e))
            except Exception as e:
                self._send_json(502, {"error": str(e)})
            return
        return super().do_GET()

    def do_POST(self):
        if self.path == "/__deepl/translate":
            try:
                length = int(self.headers.get("Content-Length", 0))
            except ValueError:
                length = 0
            raw = b""
            while len(raw) < length:
                chunk = self.rfile.read(length - len(raw))
                if not chunk:
                    break
                raw += chunk
            if not raw:
                raw = b"{}"
            try:
                payload = json.loads(raw.decode("utf-8"))
            except Exception:
                payload = {}
            key = (payload.get("key") or "").strip() or SERVER_KEY
            text = payload.get("text", "")
            target = payload.get("target_lang", "ZH")
            if not key or not text:
                self._send_json(400, {"error": "missing key or text"})
                return
            if not self._authorized(self.headers, {}, payload):
                self._send_json(401, {"error": "unauthorized: proxy token required"})
                return
            body = json.dumps({"text": [text], "target_lang": target}).encode("utf-8")
            try:
                data = self._call_deepl("POST", "/v2/translate", key, body)
                self._send_json(200, data)
            except urllib.error.HTTPError as e:
                self._send_json(e.code, self._safe_err(e))
            except Exception as e:
                self._send_json(502, {"error": str(e)})
            return
        self._send_json(404, {"error": "not found"})
        return

    @staticmethod
    def _safe_err(e):
        try:
            return json.loads(e.read().decode("utf-8"))
        except Exception:
            return {"error": str(e)}


if __name__ == "__main__":
    port = int(os.environ.get("PORT") or os.environ.get("DEEPL_PROXY_PORT")
               or (sys.argv[1] if len(sys.argv) > 1 else 8000))
    host = os.environ.get("DEEPL_PROXY_HOST", "0.0.0.0")
    print(f"English Learning App (DeepL proxy) -> http://{host}:{port}")
    if TOKEN:
        print("代理 Token 保护已启用：翻译请求需携带 X-Proxy-Token 或 token 参数。")
    if SERVER_KEY:
        print("服务器端 DeepL 密钥已配置：网页无需填写 DeepL 密钥即可使用。")
    else:
        print("提示：未设置 DEEPL_PROXY_TOKEN，代理对外开放（仅建议本地/可信网络使用）。")
    print("Ctrl+C 退出。")
    ThreadingHTTPServer((host, port), Handler).serve_forever()
