#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import hmac
import mimetypes
import os
import posixpath
import re
import secrets
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse


HOST = "127.0.0.1"
PORT = int(os.environ.get("ASSET_CLASS_PORT", "18082"))
BASE_PATH = "/Asset_Class"
WEB_ROOT = Path(os.environ.get("ASSET_CLASS_WEB_ROOT", "/data/www/Asset_Class")).resolve()
USERNAME = os.environ.get("ASSET_CLASS_USER", "HCTZ")
PASSWORD_HASH = os.environ.get(
    "ASSET_CLASS_PASSWORD_HASH",
    "19aa56f1fd5064d3a1df2f90e803466e2c7a1609336570b3489be938ee5d8c99",
)
PAGE_TOKEN_TTL = int(os.environ.get("ASSET_CLASS_PAGE_TOKEN_TTL", "1800"))
ASSET_TOKEN_TTL = int(os.environ.get("ASSET_CLASS_ASSET_TOKEN_TTL", "1800"))

PAGE_TOKENS: dict[str, tuple[str, float]] = {}
ASSET_TOKENS: dict[str, float] = {}


def clean_tokens() -> None:
    now = time.time()
    for token, (_, expires_at) in list(PAGE_TOKENS.items()):
        if expires_at < now:
            PAGE_TOKENS.pop(token, None)
    for token, expires_at in list(ASSET_TOKENS.items()):
        if expires_at < now:
            ASSET_TOKENS.pop(token, None)


def make_page_token(path: str) -> str:
    token = secrets.token_urlsafe(24)
    PAGE_TOKENS[token] = (normalize_site_path(path), time.time() + PAGE_TOKEN_TTL)
    return token


def consume_page_token(token: str, path: str) -> bool:
    clean_tokens()
    expected = PAGE_TOKENS.pop(token, None)
    if not expected:
        return False
    expected_path, expires_at = expected
    return expires_at >= time.time() and hmac.compare_digest(
        expected_path.encode("utf-8"),
        normalize_site_path(path).encode("utf-8"),
    )


def make_asset_token() -> str:
    token = secrets.token_urlsafe(24)
    ASSET_TOKENS[token] = time.time() + ASSET_TOKEN_TTL
    return token


def valid_asset_token(token: str) -> bool:
    clean_tokens()
    expires_at = ASSET_TOKENS.get(token)
    return bool(expires_at and expires_at >= time.time())


def normalize_site_path(raw_path: str) -> str:
    decoded = unquote(str(raw_path or "index.html")).replace("\\", "/")
    if decoded.startswith(BASE_PATH + "/"):
        decoded = decoded[len(BASE_PATH) + 1 :]
    decoded = decoded.lstrip("/")
    if decoded in {"", "."}:
        decoded = "index.html"
    normalized = posixpath.normpath(decoded)
    if normalized == ".":
        normalized = "index.html"
    if normalized.endswith("/"):
        normalized += "index.html"
    return normalized


def safe_local_path(raw_path: str) -> Path | None:
    rel_path = normalize_site_path(raw_path)
    if rel_path.startswith("../") or rel_path == "..":
        return None
    target = (WEB_ROOT / Path(rel_path)).resolve()
    try:
        target.relative_to(WEB_ROOT)
    except ValueError:
        return None
    if target.is_dir():
        target = target / "index.html"
    return target


def split_url(value: str) -> tuple[str, str, str]:
    match = re.match(r"^([^?#]*)(\?[^#]*)?(#.*)?$", value)
    if not match:
        return value, "", ""
    return match.group(1), match.group(2) or "", match.group(3) or ""


def is_external_url(value: str) -> bool:
    lower = value.strip().lower()
    return (
        not lower
        or lower.startswith("#")
        or lower.startswith(("http://", "https://", "data:", "mailto:", "tel:", "javascript:"))
    )


def resolve_relative_url(value: str, current_path: str) -> tuple[str, str] | None:
    if is_external_url(value):
        return None

    path_part, query_part, hash_part = split_url(value)
    if path_part.startswith(BASE_PATH + "/"):
        rel = path_part[len(BASE_PATH) + 1 :]
    elif path_part.startswith("/"):
        return None
    else:
        current_dir = posixpath.dirname(normalize_site_path(current_path))
        rel = posixpath.join(current_dir, path_part) if current_dir else path_part

    rel = normalize_site_path(rel)
    if rel.startswith("../") or rel == "..":
        return None
    return rel + query_part, hash_part


def is_html_path(path: str) -> bool:
    clean_path, _, _ = split_url(path)
    return clean_path.lower().endswith(".html") or "." not in posixpath.basename(clean_path)


def page_url(path: str, hash_part: str = "") -> str:
    token = make_page_token(path)
    return f"{BASE_PATH}/_page?p={quote(normalize_site_path(path), safe='')}&t={quote(token)}{hash_part}"


def asset_url(path: str, token: str) -> str:
    return f"{BASE_PATH}/_asset?p={quote(normalize_site_path(path), safe='')}&t={quote(token)}"


def rewrite_html(html: str, current_path: str) -> str:
    asset_token = make_asset_token()

    def replace_attr(match: re.Match[str]) -> str:
        attr = match.group("attr")
        quote_char = match.group("quote")
        value = match.group("value")
        resolved = resolve_relative_url(value, current_path)
        if not resolved:
            return match.group(0)
        rel_with_query, hash_part = resolved
        rel_path, query_part, _ = split_url(rel_with_query)
        if attr.lower() == "href" and is_html_path(rel_path):
            new_value = page_url(rel_path, hash_part)
        else:
            new_value = asset_url(rel_path + query_part, asset_token) + hash_part
        return f'{attr}={quote_char}{new_value}{quote_char}'

    html = re.sub(
        r'(?P<attr>\b(?:href|src|data-image-src))=(?P<quote>["\'])(?P<value>.*?)(?P=quote)',
        replace_attr,
        html,
        flags=re.IGNORECASE,
    )

    data_json_path = normalize_site_path(posixpath.join(posixpath.dirname(normalize_site_path(current_path)), "data.json"))
    data_json_url = asset_url(data_json_path, asset_token)
    html = html.replace('fetch("./data.json")', f'fetch("{data_json_url}")')
    html = html.replace("fetch('./data.json')", f"fetch('{data_json_url}')")
    html = html.replace('fetch("data.json")', f'fetch("{data_json_url}")')
    html = html.replace("fetch('data.json')", f"fetch('{data_json_url}')")

    no_cache_meta = (
        '<meta http-equiv="Cache-Control" content="no-store">\n'
        '<meta http-equiv="Pragma" content="no-cache">\n'
        '<meta http-equiv="Expires" content="0">'
    )
    if "</head>" in html:
        html = html.replace("</head>", f"{no_cache_meta}\n</head>", 1)
    return html


def login_html(error: str = "") -> bytes:
    error_html = f'<p class="error" id="error" aria-live="polite">{error}</p>' if error else '<p class="error" id="error" aria-live="polite"></p>'
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Cache-Control" content="no-store">
<meta http-equiv="Pragma" content="no-cache">
<meta http-equiv="Expires" content="0">
<title>普林格新四核轮动组合</title>
<style>
*{{box-sizing:border-box}}
html,body{{height:100%}}
body{{
  margin:0;
  background:#eef0f2;
  color:#151515;
  font-family:"Microsoft YaHei","PingFang SC","Hiragino Sans GB",Arial,sans-serif;
}}
.login-wrap{{
  min-height:100%;
  display:grid;
  place-items:center;
  padding:24px;
}}
.login-panel{{
  width:min(674px,100%);
  background:#fff;
  border:1px solid #dcdfe3;
  box-shadow:0 18px 42px rgba(12,18,28,.12);
  padding:46px 44px 52px;
}}
.brand{{
  display:flex;
  align-items:center;
  gap:18px;
  margin-bottom:32px;
}}
.brand-mark{{
  width:38px;
  height:36px;
  background:#d41414;
  flex:0 0 auto;
}}
h1{{
  margin:0;
  font-size:29px;
  line-height:1.25;
  font-weight:900;
  letter-spacing:0;
}}
.field{{
  display:grid;
  gap:10px;
  margin-top:22px;
}}
label{{
  color:#4f5660;
  font-size:20px;
}}
input{{
  width:100%;
  height:67px;
  border:1px solid #cfd4da;
  padding:0 14px;
  font:inherit;
  font-size:20px;
  outline:none;
  border-radius:0;
  background:#fff;
}}
input:focus{{
  border-color:#151515;
  box-shadow:0 0 0 3px rgba(212,20,20,.1);
}}
button{{
  width:100%;
  height:68px;
  margin-top:32px;
  border:1px solid #151515;
  background:#151515;
  color:#fff;
  font:inherit;
  font-size:28px;
  cursor:pointer;
}}
button:hover{{background:#000}}
.error{{
  min-height:22px;
  margin:14px 0 0;
  color:#c91616;
  font-size:15px;
}}
@media (max-width:640px){{
  .login-panel{{padding:30px 22px 34px}}
  .brand{{gap:12px;margin-bottom:24px}}
  .brand-mark{{width:28px;height:28px}}
  h1{{font-size:22px}}
  label{{font-size:16px}}
  input{{height:52px;font-size:17px}}
  button{{height:54px;font-size:21px}}
}}
</style>
</head>
<body>
<main class="login-wrap">
  <form class="login-panel" id="loginForm" autocomplete="off">
    <div class="brand">
      <span class="brand-mark" aria-hidden="true"></span>
      <h1>普林格新四核轮动组合</h1>
    </div>
    <div class="field">
      <label for="username">用户名</label>
      <input id="username" name="username" autocomplete="off" required autofocus>
    </div>
    <div class="field">
      <label for="password">密码</label>
      <input id="password" name="password" type="password" autocomplete="new-password" required>
    </div>
    <button type="submit">登录</button>
    {error_html}
  </form>
</main>
<script>
const form = document.getElementById("loginForm");
const error = document.getElementById("error");
form.addEventListener("submit", async (event) => {{
  event.preventDefault();
  error.textContent = "";
  const username = document.getElementById("username").value.trim();
  const password = document.getElementById("password").value;
  const body = new URLSearchParams({{ username, password }});
  const response = await fetch("{BASE_PATH}/login", {{
    method: "POST",
    headers: {{ "Content-Type": "application/x-www-form-urlencoded" }},
    body,
    cache: "no-store"
  }});
  if (response.ok) {{
    location.replace(await response.text());
  }} else {{
    error.textContent = await response.text() || "用户名或密码错误";
    document.getElementById("password").value = "";
  }}
}});
</script>
</body>
</html>""".encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    server_version = "AssetClassGate/1.0"

    def log_message(self, fmt: str, *args) -> None:
        return

    def send_no_store_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.send_header("X-Robots-Tag", "noindex, nofollow, noarchive")

    def send_bytes(self, body: bytes, content_type: str, status: HTTPStatus = HTTPStatus.OK, extra_headers: dict[str, str] | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_no_store_headers()
        for key, value in (extra_headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def redirect_login(self) -> None:
        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", BASE_PATH + "/")
        self.send_no_store_headers()
        self.end_headers()

    def do_HEAD(self) -> None:
        self.do_GET()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path == BASE_PATH + "/healthz":
            self.send_response(HTTPStatus.NO_CONTENT)
            self.send_no_store_headers()
            self.end_headers()
            return

        if path == BASE_PATH:
            self.send_response(HTTPStatus.MOVED_PERMANENTLY)
            self.send_header("Location", BASE_PATH + "/")
            self.send_no_store_headers()
            self.end_headers()
            return

        if path == BASE_PATH + "/":
            self.send_bytes(login_html(), "text/html; charset=utf-8")
            return

        if path == BASE_PATH + "/_page":
            params = parse_qs(parsed.query)
            rel_path = normalize_site_path(params.get("p", ["index.html"])[0])
            token = params.get("t", [""])[0]
            if not consume_page_token(token, rel_path):
                self.redirect_login()
                return
            self.serve_page(rel_path)
            return

        if path == BASE_PATH + "/_asset":
            params = parse_qs(parsed.query)
            rel_path = normalize_site_path(params.get("p", [""])[0])
            token = params.get("t", [""])[0]
            if not valid_asset_token(token):
                self.send_bytes(b"Unauthorized", "text/plain; charset=utf-8", HTTPStatus.UNAUTHORIZED)
                return
            self.serve_asset(rel_path)
            return

        self.redirect_login()

    def do_POST(self) -> None:
        if urlparse(self.path).path != BASE_PATH + "/login":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8", "replace")
        fields = parse_qs(raw)
        username = fields.get("username", [""])[0].strip()
        password = fields.get("password", [""])[0]
        password_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()

        if hmac.compare_digest(username, USERNAME) and hmac.compare_digest(password_hash, PASSWORD_HASH):
            body = page_url("index.html").encode("utf-8")
            self.send_bytes(body, "text/plain; charset=utf-8")
            return

        self.send_bytes("用户名或密码错误".encode("utf-8"), "text/plain; charset=utf-8", HTTPStatus.UNAUTHORIZED)

    def serve_page(self, rel_path: str) -> None:
        local_path = safe_local_path(rel_path)
        if not local_path or not local_path.is_file() or local_path.suffix.lower() != ".html":
            self.redirect_login()
            return
        text = local_path.read_text(encoding="utf-8", errors="ignore")
        body = rewrite_html(text, rel_path).encode("utf-8")
        self.send_bytes(body, "text/html; charset=utf-8")

    def serve_asset(self, rel_path: str) -> None:
        local_path = safe_local_path(rel_path)
        if not local_path or not local_path.is_file() or local_path.suffix.lower() == ".html":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content_type = mimetypes.guess_type(str(local_path))[0] or "application/octet-stream"
        headers = {}
        if local_path.suffix.lower() in {".docx", ".xlsx", ".xls", ".csv", ".md"}:
            headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{quote(local_path.name)}"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(local_path.stat().st_size))
        self.send_no_store_headers()
        for key, value in headers.items():
            self.send_header(key, value)
        self.end_headers()
        if self.command == "HEAD":
            return
        with local_path.open("rb") as file:
            while True:
                chunk = file.read(1024 * 128)
                if not chunk:
                    break
                self.wfile.write(chunk)


if __name__ == "__main__":
    WEB_ROOT.mkdir(parents=True, exist_ok=True)
    print(f"Asset Class auth gate listening on {HOST}:{PORT}", flush=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
