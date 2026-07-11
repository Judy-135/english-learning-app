# 部署到 Render（免费，公网可用 DeepL）

目标：把 `deepl_proxy.py`（同时托管网页 + 转发 DeepL）跑在 Render 免费 Web Service 上，
得到一个任何人可访问、且能用 DeepL 翻译的公网链接。

## 步骤
1. 注册 Render：https://render.com （用 GitHub 账号登录最方便，免费）。
2. 把本目录（`english-learning-app/`）推到你自己的 GitHub 仓库
   （例如新建仓库 `english-learning-app`，把目录下所有文件提交上去）。
3. 在 Render 控制台：
   - New → **Blueprints** → 选择该 GitHub 仓库 → Render 会自动读取 `render.yaml` 创建服务；
   - 或 New → **Web Service** → 连仓库，手动填：
     - Runtime: Python 3
     - Build Command: `pip install -r requirements.txt`
     - Start Command: `python3 deepl_proxy.py`
     - 端口由 Render 自动注入 `PORT` 环境变量（代码已支持）。
4. 在服务的 **Environment** 里添加变量 `DEEPL_PROXY_TOKEN`，值填一段随机字符串
   （例如 `openssl rand -hex 16` 生成的），这是代理访问 Token，防止别人盗用你的 DeepL 额度。
5. 部署完成后，Render 会给你一个公网地址（如 `https://english-learning-app.onrender.com`）。

## 使用
- 打开该公网地址 → 右上角⚙️「设置」：
  - **DeepL 免费 API 密钥**：填你的 `:fx` 密钥；
  - **代理访问 Token**：填与第 4 步 `DEEPL_PROXY_TOKEN` 完全相同的字符串；
  - 点「保存并测试」→ 应显示「DeepL 连接正常」。
- 之后所有人通过该链接都能用 DeepL 高质量翻译（受你的代理 Token 与 DeepL 额度保护）。

## 注意
- 免费版空闲 15 分钟后休眠，首次访问会冷启动（约几秒），属正常现象。
- DeepL 密钥保存在访客浏览器 localStorage；代理 Token 是服务端共享密钥，
  只应告诉可信任的人，否则他人可借你的代理消耗 DeepL 额度。
- 不填 `DEEPL_PROXY_TOKEN` 也能跑（代理对外开放，仅建议本地/可信网络）。
