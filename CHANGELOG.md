# Changelog

所有重要改动记录在这里。版本号采用 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

---

## [0.1.0] — 2026-04-17（首次开源发布）

🎉 **首个公开版本**。经过 6 周密集迭代，从私人求职工具演进为可被任何人 Fork 使用的通用求职一体化 webapp。

### ✨ 新增

- **完整的 Apple × Nature UI 设计系统**
  - 20 节全局 CSS override（按钮 / 表单 / 表格 / Tab / Alert 等）
  - 29 个公开组件（`soft_stat_card` / `score_hero_card` / `funnel_stage_card` / `task_action_card` / `feature_card` / `diagnostic_alert` / `alert_success` 等 4 alias）
  - 20+ 设计 token（颜色 / 间距 / 圆角 / 阴影 / 字体）
  - Apple Material Motion 动效：`cubic-bezier(0.4, 0, 0.2, 1)` 缓动、按钮 active `scale(0.98)`、focus 3px 蓝外环
- **17 页功能完整**：首页 / 数据分析 / 3 JD 页 / 4 简历页 / 3 投递页 / 2 面试页 / 设置
- **用户画像配置层**（`data/user_profile.yaml`）— 所有邮件/简历/面试 prompt 从画像注入
- **设置页**加「测试连接」按钮 — 点一下验证 API Key / 端点 / 模型
- **目标公司管理** — P0/P1/排除清单 + 内推码（UI 里增删改）
- **BYO-Key Demo 模式**（`DEMO_MODE=true`）— 公网部署强制用户自带 Key
- **Dockerfile** — 一键部署到 HuggingFace Spaces / Railway / 个人 VPS
- **完整开源文档**：`README.md` / `DEPLOY.md` / `CONTRIBUTING.md` / `LICENSE`(MIT)

### 🛠 改动

- Sidebar 去黑话：`总览 → 仪表盘` / `职位情报 → 目标岗位` / `简历中心 → 简历管理` / `求职管道 → 投递进度`
- 单字按钮改短语：`投 → 标记已投递` / `回 → 取消投递` / `排 → 排除` / `生 → 生成简历`
- 全站 ~93 处原生 `st.error/success/warning/info` 统一为 `alert_*` 组件
- 全站 9 处 `st.metric` 替换为 `soft_stat_card`
- resume 模板硬编码灰色（`#444 / #666 / #888`）统一为 `#6e6e73`(TEXT_MUTED)
- `.env.example` 补齐注释 + demo 模式说明

### 🔒 隐私与安全

- 项目根 `.gitignore` 严格排除 `data/*.db*` / `CLAUDE.md` / `.claude/` / `reports/` / `linkedin/` 等所有私人数据
- `web/services/outreach_templates.py` 改为从 `user_profile` 读取姓名/学校，不硬编码任何个人信息
- 作者个人 resume HTML 模板（5 个）全部删除，只保留 `resume_default_tmpl.html` 通用 Jinja2 模板
- `data/resume_master.example.json` / `data/user_profile.example.yaml` / `data/target_companies.example.yaml` — 所有私人配置都提供 `.example.*` 公开模板

### 🐛 修复（round-2 期间发现的）

- `<a>` 内嵌 `<div>` 被 Markdown parser 切块 — 全部改用 `<span display:block>`
- `font-family:"SF Pro Display"` 双引号嵌 HTML 属性 → 破坏属性边界（修复为单引号）
- `stDownloadButton` 未被按钮 CSS 覆盖，呈红色 → 补全 Apple 白底
- `home.py` feature_card 去重（删除与 task_action_card 冲突的 3 张）
- home.py 常用入口冗余去重（2×3 → 1×3）

---

## 未来版本（roadmap）

### [0.2.0] 计划中
- [ ] 支持 OpenAI / Gemini / LiteLLM 抽象层
- [ ] Onboarding 引导页（首启动 4 步向导）
- [ ] 英文 UI
- [ ] 主简历 PDF 上传解析失败时 fallback 到手填

### [0.3.0] 远期
- [ ] PWA 离线模式
- [ ] 社区功能（故事库共享）
- [ ] 移动端响应式
