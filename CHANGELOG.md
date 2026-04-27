# Changelog

所有重要改动记录在这里。版本号采用 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

---

## [0.6.0] — 2026-04-26（公网修复闭环 · 4 大问题域 + P-1 隐私 + SDK 摘除）

### 🛠 4 大问题域全修

1. **`openai` SDK 永久摘除** — `_OAClientStub` (2 字段 dataclass) 替代 `openai.OpenAI()`，`requirements.txt` 移除 `openai` 依赖。核心调用早就走 `httpx /v1/responses`，SDK 只是 `{api_key, base_url}` 容器。彻底告别「Streamlit Cloud pip 装 openai 偶发失败 → app 启动报 RuntimeError」。
2. **公网隐私防护（P-1 critical）** — `DEMO_MODE` 下每个浏览器 session 首次访问时 wipe 12 张用户私有表（`resume_master` / `resume_versions` / `generated_resumes` / `applications` / `contacts` / `linkedin_leads` / `email_queue` / `interview_prep` / `interview_qa` / `star_pool` / `star_stories` / `jd_evaluations`）。`st.session_state["_demo_wipe_done"]` flag 保证 rerun-safe，同 session 内不重复 wipe。
3. **简历解析丢字段三连修** — NFKC unicode 归一化（消康熙部首 `U+2F00-U+2FDF`）+ `force_overwrite=True` 强制覆盖前次残留 + 行内章节切分（long ≥4 字符无前置边界 / short <4 字符严格边界）+ **CJK Radicals Supplement → 本字映射兜底**（v0.4.1 followup，覆盖 NFKC 漏掉的 `U+2E80-U+2EFF` 区段）。
4. **响应式宽度** — `max-width: 1080px` → `min(96vw, 1480px)`，27 寸屏从中间 1/3 占满到 ~80%。

### 🛠 Quality 降级

- projects / internships / education 缺失从 `reasons` 降级为 `warnings`（只剩"姓名为空"硬阻断 auto-save）
- 应届生（无项目）/ 跨行业（无实习）的简历也能上传成功

### 🐛 AI 对话 4 处 bug 修

- chat content `html.escape` 防 `<` `&` 破渲染
- pending patch 渲染 try/except + 失败自动撤销
- 显式 `intent == "error"` 分支让真错误可见
- 兜底未知 intent

### 🗑 删 PDF 预览

- `master_resume.py` + `resume_tailor.py` 两处 base64 iframe expander 移除（保留 DB `original_docx_blob` 供 DOCX 重写）

### 🧪 测试样本库

- 新增 `OFFER/tests_samples/` 目录：3 PDF + 2 JD + 3 历史 JSON 样本，配 README

### 提交链

`7c6fd23 → bfd89b0 → a4aaa4d → 7700fa0 → fe26b5b → 97b0bec → 8013e29 → 8439c14 → e0d778d → d69b82e`

---

## [0.5.0] — 2026-04-21（简历规则 v2.3 · 内容书写规则沉淀）

### ✨ 新增

- **`web/prompts/resume_writing_rules.md`** —— 简历内容书写规则（11 节）
  - 语气与口吻（人称 / 时态 / 句式节奏 / DEAI 禁用词）
  - **STAR 法则的简历变形**（S+T 压进 header/label，A+R 写 bullet）
  - **拿到新经历 → 转成 bullet 的 6 步法**（5 问 → 筛 2-4 条 → 取 label → 写动作 → 写结果 → 压行）
  - Bullet 模板库（运营复盘 / 海外冷启动 / AI 工具 / 跨团队 / 开源作品 5 种高频场景）
  - **个人总结 5 槽位模板**（身份钩子 / 核心数据 / 工具栈 / 经历覆盖面 / 能力锚点）
  - 数字写作规则（字面保留 / 组合写法 / 放置策略）
  - 专业技能写作规则
  - 经历排序与取舍（项目按 JD 相关性，实习按时间倒序）
  - 投递前 10 步 JD 匹配检查
  - **5 类常见错误与改写示范**
  - 快速自检清单

### 🛠 改动

- `resume_prompt_rules.py` 版本号升至 v2.3，顶部引用更新为"四件套"
- `CLAUDE.md` "规则文档三件套" → "规则文档四件套"

---

## [0.4.0] — 2026-04-20（简历规则 v2.2 · 排版布局规范沉淀）

### ✨ 新增

- **`web/prompts/resume_layout_rules.md`** —— 基于同花顺版定稿提炼的完整排版规范（11 节）
  - 页面与排版基线（A4 / 字号 / 行高）
  - 头部区双列布局（左：姓名+联系+意向；右：证件照）
  - 5 大 section 固定顺序（总结 → 项目 → 实习 → 技能 → 教育）
  - 个人总结写作模板（70–140 字，身份+数据+工具+实习+软素质）
  - 项目/实习 bullet 结构（`**label：** 正文`）+ 动词偏好表
  - 专业技能 3 行硬约束（超过就合并分类）
  - 教育背景 1 行压缩（禁三段式 header）
  - 超链视觉去蓝规则（`color: inherit; text-decoration: none;`）
  - **压页策略**（7 步从轻到重的取舍顺序）
  - 每次定制新 JD 的 10 步工作流

### 🛠 改动

- `resume_prompt_rules.py` 版本号升至 v2.2，顶部引用新增 layout 文件
- `CLAUDE.md` 增补"规则文档三件套"引用

### 📋 同花顺版定制简历交付

- `/Users/Zhuanz/Desktop/OFFER/杨超_简历_同花顺版.pdf`（一页 A4 · 含头像 · 纯黑超链）
- `/Users/Zhuanz/Desktop/OFFER/杨超_简历_同花顺版.docx`（可编辑 · 头像表格嵌入）
- 生成脚本：`/Users/Zhuanz/Desktop/OFFER/_gen_resume_docx_同花顺.py`

---

## [0.3.0] — 2026-04-20（Codex/OpenAI 兼容层 · 公开池试玩）

### ✨ 新增

- **OpenAICompatClient 适配层** `web/services/llm_client.py`
  - 业务层继续用 Anthropic 签名 (`client.messages.create`)，底层按 provider 路由
  - `codex` / `openai` 两个 provider 走 `chat.completions`，自动转换 messages 格式
  - 统一 `_AnthropicLikeResponse` 包装，调用点零改动
- **provider 预设扩展**
  - 🎁 **Codex 公开池**（https://navacodex.shop/v1 · gpt-5.4）— 初期免费共享，访客开箱即用
  - **OpenAI 官方**（https://api.openai.com/v1 · gpt-4o-mini）
  - `is_openai_wire` 路由判断；`codex_shared_key` / `codex_per_session_budget_usd` 从 `st.secrets` 读取
- **公开池试玩机制**
  - 用户无 Key 但选 codex + secrets 有 `CODEX_SHARED_KEY` → 自动走共享 Key
  - session 级用量透明展示（初期阶段不做额度拦截）
  - `has_anthropic_key` 扩展为「考虑公开池可用性」
- **设置页 UI** 加 provider 下拉、公开池状态 banner、申请 Key 链接

### 🛠 改动

- `requirements.txt` 新增 `openai>=1.40`
- 默认 `llm_provider` 从 `anthropic` 改为 `codex`（新访客打开设置页默认勾选 Codex）

---

## [0.2.0] — 2026-04-20（简历规则体系 v2.0）

### ✨ 新增

- **统一规则常量** `web/services/resume_prompt_rules.py`（RULE_VERSION = "2.0"）
  - `BOLD_RULES_BRIEF`：加粗规则精简版，供 system prompt 嵌入
  - `DEAI_RULES_BRIEF`：中文语言去 AI 腔约束
  - `FULL_STYLE_RULES`：两者组合，一站式引用
- **配套文档**：
  - `web/prompts/resume_bold_rules.md` — 157 行完整加粗规范（含正误对照表、HTML 实现、自检清单）
  - `web/prompts/resume_system.md` — 嵌入 DEAI + 加粗精简规则

### 🛠 改动

- **3 处硬编码 system prompt 改为引用统一规则常量**
  - `ai_engine.py::RESUME_SYSTEM`
  - `resume_tailor.py::TAILOR_SYSTEM`
  - `resume_tailor.py::SECTION_REWRITE_SYSTEM`
- **加粗规则从「整段 `<b>数字 单位</b>`」升级为「只粗纯数字 `<b>数字</b> 单位`」**
  - 示例：`<b>9,000+</b> 粉`（而非 `<b>9,000+ 粉</b>`）
  - 过程描述（「40 分钟压到 10 分钟」「30 秒产出」）整句不加粗
  - 对比段（`<b>0 → 9,000+</b>`、`<b>1,048 万 → 1,262 万</b>`）整段加粗
- **validator 数字校验改为 token 序列对齐**（`resume_validator.py`）
  - 新增 `_extract_number_tokens()`：从整条 bullet 提取纯数字 token 集合
  - 兼容旧格式 master + 新格式 tailored，避免误报
  - 过滤配置量（「6 个模块」「3 家公司」）避免干扰

### 🧪 测试

- `python3 -m services.resume_validator` smoke test 通过
- Token 提取验证：`<b>9000+ 粉</b>` 和 `<b>9,000+</b> 粉` 都映射到 `{"9000+"}`

### 📋 Kimi 版定制简历交付

- `/Users/Zhuanz/Desktop/OFFER/杨超_简历_Kimi版.pdf`（一页 A4，针对国内社媒 KOL 增长运营实习）
- HTML 源：`杨超_简历_Kimi版.html`（Kaiti SC 姓名字体 + 灰底 section 标题 + 精细加粗）

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

### 近期
- [ ] Onboarding 引导页（首启动 4 步向导）
- [ ] 英文 UI / i18n
- [ ] Gemini / LiteLLM provider（现已支持 Anthropic / OpenAI / Codex 三路）

### 远期
- [ ] PWA 离线模式
- [ ] 社区功能（故事库共享 · 模板市场）
- [ ] 移动端响应式
