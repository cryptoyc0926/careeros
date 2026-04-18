# CareerOS — 属于你自己的 offer 网站

> 配一次 API，跑一次本地，每份简历都为岗位量身定制。

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](./LICENSE)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.38%2B-ff4b4b)](https://streamlit.io/)
[![Claude](https://img.shields.io/badge/Claude_API-Anthropic-9d6cff)](https://www.anthropic.com/)

---

## 它是什么

**CareerOS** 是一个本地跑的求职一体化 webapp。你把**主简历**和**目标岗位 JD** 丢给它，AI（Claude）会：

1. 给每个岗位算一个 **match_score**，告诉你匹配度和差距
2. **改写**你的主简历，生成该岗位量身定制的版本（保留所有硬事实不编造）
3. **输出 PDF**，直接投
4. 帮你**追踪**投递进度、生成跟进话术、准备面试

所有数据都在你自己的电脑上（SQLite 单文件），API Key 也是你自己的，作者看不到任何东西。

---

## 截图

![截图占位 — 将在 docs/screenshots/ 发布后补上](https://via.placeholder.com/900x500?text=CareerOS+Screenshots+coming+soon)

---

## 5 分钟快速开始（本地）

```bash
# 1. Clone
git clone https://github.com/<YOUR_USERNAME>/careeros.git
cd careeros

# 2. 装依赖
python -m venv venv && source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r web/requirements.txt

# 3. 拷贝 .env 模板，填入你的 Claude API Key
cp web/.env.example web/.env
# 编辑 web/.env，填 ANTHROPIC_API_KEY=sk-ant-...

# 4. 启动
streamlit run web/app.py
# → 浏览器自动打开 http://localhost:8501
```

第一次打开会引导你：

1. **填个人画像**（姓名/学校/专业/目标岗位，3 分钟）
2. **粘贴 Claude API Key**（去 [Anthropic Console](https://console.anthropic.com/) 申请，免费额度够试用）
3. **填主简历** 或上传 PDF/DOCX（系统会解析，解析失败也能手填）
4. **加第一个目标岗位**（粘贴 JD 链接或文本）
5. 点「生成定制简历」→ **下载 PDF**

---

## 核心功能

| 模块 | 能力 |
|---|---|
| 🎯 **JD 入库** | 4 种方式：粘贴链接（支持 Moka/飞书）/ AI 智能解析 / 手动 / 上传 PDF |
| 📝 **简历定制** | AI 按 JD 改写主简历，保留硬事实不编造，生成 match_score |
| 📊 **投递追踪** | 看板（已收藏/已投递/跟进中/面试/Offer）+ 漏斗 + 转化率诊断 |
| 💬 **面试准备** | STAR 故事库 / 八股题 / 群面题 / 牛客面经导入 |
| 📧 **邮件模板** | 内推 / 投递 / 跟进 三类话术一键生成（从你的个人画像注入）|
| ⭐ **STAR 素材池** | 经历沉淀为复用素材，跨岗位调度 |

---

## 在线 Demo

点击下面的按钮 Fork 到你自己的 HuggingFace 账号，一键部署你自己的实例：

[![Deploy to HF Spaces](https://huggingface.co/datasets/huggingface/badges/resolve/main/deploy-to-spaces-md.svg)](https://huggingface.co/spaces/new?template=<your_hf_username>/careeros)

> **BYO-Key（自带 Key）模式**：你用自己的 Anthropic API Key，作者不收任何费用也不保存你的任何数据。
> 详细部署指南见 [DEPLOY.md](./DEPLOY.md)。

---

## 技术栈

- **Frontend**：Streamlit 1.38+（17 个页面 / 29 个 Apple 风组件）
- **AI**：Anthropic Claude（Opus/Sonnet 均可）
- **Storage**：SQLite（纯文件，零依赖）
- **PDF**：WeasyPrint + Jinja2
- **JD 抓取**：requests + BeautifulSoup（SPA 站点可选 Playwright）
- **Python**：3.10+

---

## 术语对照（新人 3 分钟看懂）

| 术语 | 含义 |
|---|---|
| **P0 / P1 / P2** | 优先级：主攻 / 积极投递 / 备选 |
| **fit_score / 匹配分** | AI 给这个岗位 × 你主简历打的 0-100 分 |
| **STAR** | 面试故事结构：Situation · Task · Action · Result |
| **adapter** | JD 抓取模式（auto = HTML 直抓 / browser = Playwright 渲染 / manual = 手动）|
| **主简历 / 定制简历** | 主简历 = 底稿（长版本）；定制简历 = 针对具体岗位的改写版 |

---

## Roadmap

- [x] v5 Apple UI 收敛（20 节 CSS + 29 组件 + Nature × Apple 风格）
- [x] 隐私清理 + 通用化开源（v0.1.0）
- [ ] 英文版（多语言）
- [ ] 支持 OpenAI / Gemini / 本地模型（通过 LiteLLM 抽象层）
- [ ] PWA 离线模式
- [ ] 社区功能（故事库共享、模板市场）

---

## 贡献

欢迎 PR。见 [CONTRIBUTING.md](./CONTRIBUTING.md)。

**我特别希望收到的贡献**：
- 更多 resume 模板（只要没硬编码个人信息即可）
- 其他 LLM provider 的适配层
- 英文/日文本地化

---

## License

[MIT](./LICENSE) — 自由商用 / 修改 / 再分发，附上原始版权声明即可。

---

## 致谢

构建过程中大量使用 [Claude Code](https://claude.com/claude-code) 协作完成。项目结构与 UI 系统受 Linear / Nature / Apple 官网启发。
