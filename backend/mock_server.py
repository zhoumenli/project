"""A tiny mock server for API testing demos (optional)."""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI(title="Demo Mock Server")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.post("/api/login")
def login(payload: dict):
    if payload.get("username") == "admin" and payload.get("password") == "123456":
        return {"code": 0, "message": "success", "data": {"token": "mock-jwt-token-abc123"}}
    return {"code": 401, "message": "bad credentials"}


@app.get("/api/user/info")
def user_info():
    return {"code": 0, "data": {"id": 1, "name": "管理员", "role": "admin"}}


@app.api_route("/api/echo", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def echo(request: Request):
    """Echo back method / headers / query / body — handy for verifying API clients."""
    body = await request.body()
    text = body.decode("utf-8", errors="replace")
    return {
        "method": request.method,
        "headers": {k.lower(): v for k, v in request.headers.items()},
        "query": dict(request.query_params),
        "body": text[:3000],
        "content_type": request.headers.get("content-type", ""),
    }


@app.get("/api/products")
def products(page: int = 1, size: int = 10, keyword: str = ""):
    items = [
        {"id": i, "name": f"商品{i}", "price": 9.9 * i}
        for i in range(1, min(size, 10) + 1)
        if keyword in f"商品{i}"
    ]
    return {"code": 0, "page": page, "data": items}


DEMO_PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>登录 - 演示商城系统</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: "Microsoft YaHei", sans-serif; background: #f4f6fb; color: #1f2430; }
  .page { max-width: 520px; margin: 30px auto; padding: 0 16px; }
  header { text-align: center; margin-bottom: 14px; }
  h1 { font-size: 22px; }
  nav.menu { display: flex; gap: 18px; justify-content: center; margin-bottom: 24px; }
  nav.menu a { color: #4f6ef7; text-decoration: none; font-size: 14px; }
  form { background: #fff; border: 1px solid #e6e9f0; border-radius: 12px; padding: 24px; box-shadow: 0 2px 12px rgba(24,39,75,.06); }
  .field { margin-bottom: 16px; }
  .field label { display: block; font-size: 13px; color: #8a90a0; margin-bottom: 6px; }
  .field input[type=text], .field input[type=password] { width: 100%; padding: 10px 12px; border: 1px solid #e6e9f0; border-radius: 8px; font-size: 14px; }
  .checkline { display: flex; align-items: center; gap: 8px; margin-bottom: 18px; font-size: 13px; }
  .checkline label { margin: 0; color: #1f2430; }
  .btn { padding: 10px 22px; border-radius: 8px; border: none; font-size: 14px; cursor: pointer; }
  .btn.primary { background: #4f6ef7; color: #fff; width: 100%; }
  .btn.ghost { background: none; color: #8a90a0; margin-top: 10px; width: 100%; }
  .tabs { display: flex; gap: 8px; margin-top: 24px; }
  .tab-item { flex: 1; text-align: center; padding: 10px; background: #fff; border: 1px solid #e6e9f0; border-radius: 8px; font-size: 14px; cursor: pointer; }
  .tab-item.active { border-color: #4f6ef7; color: #4f6ef7; font-weight: 600; }
  .footer-note { text-align: center; margin-top: 20px; font-size: 13px; color: #8a90a0; }
  .footer-note a { color: #4f6ef7; }
</style>
</head>
<body>
<div class="page">
  <header><h1>用户登录</h1></header>
  <nav class="menu">
    <a href="#">首页</a>
    <a href="#">商品列表</a>
    <a href="#">关于我们</a>
  </nav>
  <form id="login-form">
    <div class="field">
      <label for="username">用户名</label>
      <input id="username" name="username" type="text" placeholder="请输入用户名">
    </div>
    <div class="field">
      <label for="password">密码</label>
      <input id="password" name="password" type="password" placeholder="请输入密码">
    </div>
    <div class="checkline">
      <input type="checkbox" id="remember" name="remember">
      <label for="remember">记住我</label>
    </div>
    <button id="login-btn" type="submit" class="btn primary">登录</button>
    <button type="button" class="btn ghost" onclick="alert('请联系管理员重置')">忘记密码</button>
  </form>
  <div class="tabs">
    <div class="tab-item active" data-testid="tab-product">商品列表</div>
    <div class="tab-item" data-testid="tab-order">我的订单</div>
  </div>
  <div class="footer-note">遇到问题？<a href="#">查看帮助</a></div>
</div>
</body>
</html>"""


DASHBOARD_PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"><title>控制台 - 演示商城系统</title>
<style>
  body { font-family: "Microsoft YaHei", sans-serif; background:#f4f6fb; color:#1f2430; margin:0; padding:30px; }
  .card { background:#fff; border:1px solid #e6e9f0; border-radius:12px; padding:20px; max-width:620px; margin:auto; }
  h1 { font-size:20px; margin:0 0 16px; }
  .welcome { color:#4f6ef7; font-weight:600; margin-bottom:14px; }
  table { width:100%; border-collapse:collapse; font-size:13px; }
  th,td { border:1px solid #e6e9f0; padding:8px; text-align:left; }
  th { background:#fafbfc; }
  button { padding:8px 16px; border:none; border-radius:8px; background:#4f6ef7; color:#fff; cursor:pointer; margin-top:14px; }
</style></head>
<body><div class="card">
  <h1>后台控制台</h1>
  <div class="welcome" id="welcome-text">欢迎回来，管理员</div>
  <table><thead><tr><th>订单号</th><th>金额</th><th>状态</th></tr></thead>
  <tbody><tr><td>SO-2026001</td><td>¥199.00</td><td>已完成</td></tr>
  <tr><td>SO-2026002</td><td>¥58.00</td><td>待发货</td></tr></tbody></table>
  <button id="logout-btn">退出登录</button>
</div></body></html>"""


@app.get("/demo/dashboard", response_class=HTMLResponse)
def demo_dashboard():
    return HTMLResponse(DASHBOARD_PAGE)


@app.get("/demo/login", response_class=HTMLResponse)
def demo_login_page():
    return HTMLResponse(DEMO_PAGE)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=9001)
