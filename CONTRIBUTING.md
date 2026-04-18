# 贡献指南

感谢对 CareerOS 感兴趣。以下是本项目的贡献规范。

---

## 开发环境

```bash
git clone https://github.com/cryptoyc0926/careeros.git
cd careeros
python -m venv venv && source venv/bin/activate
pip install -r web/requirements.txt

# 运行
streamlit run web/app.py
```

---

## 项目结构

```
careeros/
├── README.md                   # 项目首页
├── DEPLOY.md                   # 部署指南（HF / Railway / VPS）
├── Dockerfile                  # 容器化部署
├── LICENSE                     # MIT
├── .gitignore                  # ⚠️ 严格：所有私人数据都在排除清单
│
├── data/
│   ├── *.example.yaml / *.example.json   # 公开示例（可进仓库）
│   └── （非 example 文件不进仓库）
│
├── web/                        # Streamlit 主应用
│   ├── app.py                  # 入口 + 全局 CSS + 导航注册
│   ├── config.py               # 配置层（读 .env + user_profile.yaml）
│   ├── components/ui.py        # ⭐ 29 个 Apple 风组件 + 20 token
│   ├── pages/*.py              # 17 个功能页
│   ├── services/               # 业务逻辑（AI 定制、邮件、JD 抓取）
│   ├── models/                 # 数据库访问层
│   └── templates/              # Jinja2 简历 HTML 模板
│
└── scripts/
    ├── setup.sh                # 一键初始化
    ├── init_db.py              # 建表
    └── seed_resume_master.py   # 灌示例数据
```

---

## UI 开发红线（来自 v5 round-2 的血泪经验）

严格遵守以下规则，否则渲染会出问题：

1. **HTML 属性里字体栈永远用单引号**：`font-family:'SF Pro Text', ...`（双引号会破坏属性边界）
2. **不要在 `<a>` / `<button>` 内部嵌 `<div>`**（Markdown parser 会切开）。用 `<span style="display:block">` 代替
3. **不用 `st.metric / st.divider / st.success / st.error / st.warning / st.info` 等原生组件**，全部走 `components/ui.py` 的：
   - `soft_stat_card / summary_card_hero / funnel_stage_card` 替代 `st.metric`
   - `divider()` 替代 `st.divider()`
   - `alert_success / alert_info / alert_warning / alert_danger` 替代 `st.success/info/warning/error`
4. **Button 文案不加 emoji**（字体栈混 emoji 会失真）
5. **所有颜色走 token**（从 `components.ui` import `TEXT_STRONG / BG_SURFACE / ACCENT_BLUE / ...`），不硬编码 `#0071e3` 等

---

## PR 流程

1. Fork → 开 feature 分支：`git checkout -b feat/your-feature`
2. 写代码 + 跑本地测试（至少手动过一遍相关页面）
3. 如改了 UI，附上 before/after 截图
4. PR 描述清楚：**为什么改 + 改了什么 + 如何验证**
5. **零个人数据**：确认你没把自己的姓名/邮箱/电话/内推码/真实公司信息提交到代码。建议 PR 前用 `grep -rE "<你的姓名>|<你的邮箱>|<你的内推码>" .` 做一次全文扫描。

---

## 提 Issue

- 🐛 Bug：贴上复现步骤、Python 版本、操作系统、报错信息
- 💡 Feature：说明场景、预期行为、为什么现有功能不够
- ❓ 使用咨询：先看 README + DEPLOY 的 FAQ

---

## 常见贡献方向

- [ ] **更多 resume 模板**（在 `web/templates/` 加新的 `.html`，必须是 Jinja2 占位，不能硬编码个人信息）
- [ ] **其他 LLM provider**（OpenAI / Gemini / LiteLLM 抽象层）
- [ ] **i18n**（英文/日文）
- [ ] **Ghost JD 检测准确率优化**
- [ ] **更好的 PDF 导出**（替代 WeasyPrint 减少系统依赖）

---

## 行为准则

- 对所有贡献者保持尊重
- 技术讨论聚焦代码/方案本身
- 不鼓励讨论个人求职细节（CareerOS 是工具，求职心路历程请去别的地方分享 🙏）
