# CareerOS — Codex 协作须知

> 每次启动先读本文件 + CLAUDE.md + web/app.py（三件套进入状态）

---

## 你的角色

Codex 在本项目的职责：

1. **对抗性审查公开页面**：HF Space 和本地 `streamlit run web/app.py` 的真实交互测试
2. **浏览器实跑复现 bug**：点按钮、填表、看报错、抓 network / console
3. **代码层面的补丁式修复**：小范围 bug fix、类型错、空指针、边界条件
4. **回归测试**：改动后跑一遍关键流（登录 → 上传简历 → AI 生成 → 导出）

**不归你管**：UI 设计决策、架构重构、memory 文件维护、新功能开发（这些是 Claude 的活）。

---

## 项目快照

- **路径**：`/Users/Zhuanz/Desktop/OFFER/career-os-claudecode`
- **技术栈**：Streamlit + SQLite + BYO-Key（OpenAI / Codex responses endpoint / Claude）
- **入口**：`web/app.py`
- **页面**：`web/pages/*.py`
- **设计 token**：`web/components/ui.py`（靛蓝 `#0071e3` / 白底 `#f5f5f7` / 文字 `#1d1d1f`）
- **简历规则**：`web/services/resume_prompt_rules.py`（统一常量，改规则必读 CLAUDE.md § 简历生成规则）
- **公网部署**：HF Space（BYO-Key 模式，用户自带 key）
- **本地**：`cd web && streamlit run app.py` → `localhost:8501`

---

## 红线（违反即 revert，不讨论）

1. **FONT_SANS 必须用单引号** — 双引号会被 Streamlit HTML sanitizer 吞掉
2. **按钮不准加 emoji** — Apple 风格
3. **禁用 `st.metric` / `st.subheader`** — 风格不统一，必须用 ui.py 封装的组件
4. **不许写 `onmouseover`** — 被 strip
5. **`<a>` 不能嵌 `<div>`** — parser 会切成兄弟 block，用 `<span style="display:block">`
6. **禁改 `web/components/ui.py` 和 `.streamlit/config.toml`** — UI token 归 Claude
7. **禁改 `web/services/resume_prompt_rules.py`** — 简历规则归 Claude
8. **不许用 `git add -A`** — 逐文件 add，防止误提交 `.env` / `*.bak` / data/*.db

---

## 分工表

| 类型 | 谁做 |
|---|---|
| 新页面、新功能 | Claude |
| UI 重构、设计 token 调整 | Claude |
| 简历 prompt 规则改动 | Claude |
| memory / INDEX.md 维护 | Claude |
| bug 复现 + 最小补丁 | **Codex** |
| 浏览器实跑验收 | **Codex** |
| 回归测试脚本 | **Codex** |
| HF Space 公网问题排查 | **Codex** |

---

## 交接协议

- 每次 Codex 改完代码，**必须**在 `web/NOTES_CODEX.md` 追加一行：
  ```
  2026-04-20 | fix | web/pages/xxx.py | 描述一句话
  ```
- 大改（>50 行或跨文件）在 NOTES_CODEX.md 写一段说明
- Claude 每次启动会扫 NOTES_CODEX.md 最近 10 行，了解 Codex 动过什么

---

## Codex 启动咒语模板

用户会用这样的 prompt 调你：

```
项目：/Users/Zhuanz/Desktop/OFFER/career-os-claudecode
先读 CODEX.md 和 CLAUDE.md，再读 web/app.py。
红线在 CODEX.md，违反直接 revert。

本次任务：<具体描述>
验证方式：<浏览器实跑 / pytest / 截图>
完成标准：<可观测的结果>

改完在 web/NOTES_CODEX.md 追加一行。
```

---

## 三条预置任务模板

### 1. 对抗性审查（公网页面扫雷）

```
任务：对 HF Space 部署版做对抗性审查。
步骤：
  1) 浏览器打开 https://<hf-space-url>
  2) 挨个点 sidebar 每个页面，记录 console 报错 / 渲染异常 / 交互卡死
  3) 重点查：BYO-Key 输入后能否真实调通 / 简历上传 / AI 生成按钮
  4) 产出 bug 清单：文件路径 + 行号 + 复现步骤 + 建议修复
完成标准：一份 markdown 报告，至少覆盖 5 个页面。
不改代码，只出报告。
```

### 2. Bug 修复（小范围补丁）

```
任务：修 <具体 bug 描述>
约束：
  - 只改最小必要文件
  - 不动 UI token / 不动简历规则
  - 改完本地 streamlit run 验证一次
  - 在 web/NOTES_CODEX.md 记录
完成标准：复现步骤不再触发 bug。
```

### 3. 回归测试

```
任务：跑关键流回归。
关键流：
  1) 启动 → 首页加载无 console error
  2) 设置页填 BYO-Key → 测试连接按钮返回成功
  3) 上传简历 md → AI 生成 → 导出 docx
  4) 岗位池页面渲染 + 筛选
产出：每一步截图 + pass/fail 表格。
发现问题只记录，不修（交给 Claude 分配）。
```

---

## 已知坑（踩过的别再踩）

- Streamlit file_uploader 在 iframe 内 1x1 hidden，Chrome MCP 和 JS 注入都无法上传文件 → 必须让用户手动上传
- `gpt-5.4` 模型必须走 `/v1/responses` 端点，不是 `/v1/chat/completions`
- `navacodex.shop` 是用户自己的 API 代理，不是官方 OpenAI
- BYO-Key 模式下 key 存在 `st.session_state`，不写磁盘
- `.env.bak` 曾经泄露过 key，已加入 .gitignore 黑名单
