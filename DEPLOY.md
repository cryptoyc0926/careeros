# CareerOS 部署指南

三种部署方式，按你的需求挑一个。

---

## 方案 1：本地运行（推荐新手 · 最快 5 分钟）

**适合**：只给自己用；想充分利用本地 SQLite 数据持久化；想用 Playwright 抓 SPA 站点 JD。

```bash
git clone https://github.com/cryptoyc0926/careeros.git
cd careeros

python -m venv venv && source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r web/requirements.txt

cp web/.env.example web/.env
# 编辑 web/.env，填入 ANTHROPIC_API_KEY

streamlit run web/app.py
```

可选：如果你需要抓 Moka/飞书/Boss 等 SPA 招聘网站的 JD：

```bash
pip install playwright
playwright install chromium
```

---

## 方案 2：HuggingFace Spaces（推荐在线 demo · 免费 · 无需信用卡）

**适合**：想把自己的 CareerOS 实例放公网，随时随地用；想让朋友试用。

### 步骤

1. Fork 本仓库到你的 GitHub
2. 登录 [HuggingFace](https://huggingface.co/)（免费注册）
3. 点 **New Space** → 填名字 → **Space SDK 选 Docker**
4. **Source**：选 "Clone from another Hub Space / GitHub repo"，粘贴你的 fork URL
5. 进入 Space **Settings → Variables and secrets → New secret**：
   - 如果不想放 Key 在代码里（推荐），留空，**每次访问时在设置页填 Key**（BYO-Key 模式）
   - 或设 `ANTHROPIC_API_KEY=sk-ant-xxx`（单人用自己的 Space 可以）
6. 等 Docker build 完（3-5 分钟首次构建），点 **App** tab 进入你的在线实例

### 注意

- HuggingFace 免费 Space 有 **12 小时无访问休眠**，下次访问冷启动 5-10 秒
- 数据库挂在容器的 `/data`，**重启后保留**（HF 自动持久化）
- SPA 抓取（Playwright）可能因容器资源受限需要手动调，推荐改用"智能粘贴"模式

---

## 方案 3：Railway / Render / VPS（付费长期运营）

**适合**：要做成正式的在线服务；需要 Postgres 替代 SQLite；需要多人协作。

### Railway

1. [Railway](https://railway.app) 登录 → **New Project → Deploy from GitHub**
2. 选你的 fork
3. Railway 自动检测 `Dockerfile` 开始 build
4. 加环境变量 `ANTHROPIC_API_KEY` 和 `DEMO_MODE=false`
5. 可选：**Add PostgreSQL plugin**，通过 `DATABASE_URL` 替代 SQLite（需改 `web/models/database.py` 的连接层）

### 个人 VPS（阿里云/腾讯云/Vultr）

```bash
# 服务器上
git clone https://github.com/cryptoyc0926/careeros.git
cd careeros
docker build -t careeros .
docker run -d \
  -p 80:7860 \
  -v /data/careeros:/data \
  --env-file .env \
  --name careeros careeros
```

（推荐在前面套一层 Caddy/Nginx 做 HTTPS）

---

## 环境变量清单

| 变量名 | 必填 | 说明 |
|---|---|---|
| `ANTHROPIC_API_KEY` | 是（或在 UI 里填） | Claude API Key |
| `ANTHROPIC_BASE_URL` | 否 | 自定义 API 代理地址（留空走官方） |
| `CLAUDE_MODEL` | 否 | 默认 `claude-opus-4-6`，可换 `claude-sonnet-4-6` 省钱 |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` | 否 | 发邮件必填；不填就只能预览 |
| `DEMO_MODE` | 否 | `true` = BYO-Key + 禁真实邮件发送（公网 demo 推荐）|
| `DB_PATH` | 否 | SQLite 路径，默认 `../data/career_os.db` |

---

## 常见问题

### Q: Claude API Key 怎么拿？

去 [https://console.anthropic.com/](https://console.anthropic.com/) 注册，**有 5 美元免费额度**，跑几十次简历定制没问题。

### Q: 支持国内代理吗？

支持。在**设置 → Claude API 配置**里填 `ANTHROPIC_BASE_URL`，格式 `https://your-proxy.com`。

### Q: 数据会泄露给作者吗？

**不会。** 项目纯开源，数据全部在你的本地 SQLite 或你自己的 HF Space 容器里，代码里没有任何外发到作者服务器的 URL。API 调用直接走 Anthropic 官方或你配的代理。

### Q: 能改成 OpenAI 或 Gemini 吗？

目前硬绑 Anthropic SDK。Roadmap 里会加 LiteLLM 抽象层（PR 欢迎）。

### Q: Playwright 在 HF Spaces 装不上怎么办？

无视这个报错，用"**智能粘贴**" tab：把 JD 页面内容复制进去，AI 会自动提取公司/岗位/描述。实测覆盖 95% 场景。
