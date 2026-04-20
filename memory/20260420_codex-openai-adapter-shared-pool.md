---
date: 2026-04-20
session_id: ec686a53
topic: codex-openai-adapter-shared-pool
files_touched:
  - web/services/llm_client.py
  - web/config.py
  - web/pages/settings_page.py
  - web/prompts/resume_bold_rules.md
  - web/services/resume_prompt_rules.py
  - requirements.txt
decisions:
  - 公开池预算单位确认为美元（$10/月总额度，$0.5/session 单访客）
  - 防刷方案选 Turnstile+KV（方案C），暂未实现，留待后续
  - 额度用完策略：公开试玩池 + BYO-Key fallback，不锁死
  - Codex provider 排首位（面向新用户的默认推荐入口）
  - 业务层保持 Anthropic 签名不变，OpenAI wire 透明适配
blockers_resolved:
  - llm_client 原本强依赖 anthropic SDK import → 改为防御性 import，OpenAI 异常也能走 friendly_error
  - has_anthropic_key 原本只看 ANTHROPIC_API_KEY 字段，公开池用户无 Key 导致所有功能被拒 → 扩展为：provider=codex 且 secrets 有 CODEX_SHARED_KEY 时视为可用
  - friendly_error 原本直接 from anthropic import … 在 OpenAI-wire 路径下会抛 ImportError → 改为 try/except 包裹，先做字符串级异常判断
new_user_preferences:
  - 决策选项用填空题形式给出（如：□方案A □方案B），用户选好后直接执行，不需要再确认
tags: [careeros, llm, openai, codex, shared-pool, byo-key, streamlit]
---

# CareerOS 接入 OpenAI 协议 + Codex 公开池试玩

## 做了什么
- 在 llm_client.py 新增 OpenAICompatClient adapter：业务层继续调 `client.messages.create()`，OpenAI-wire provider 底层透明路由到 `chat.completions.create()`，响应包装为 `_AnthropicLikeResponse`
- config.py 新增 `is_openai_wire` property、`codex_shared_key` / `codex_per_session_budget_usd` 读 st.secrets；`has_anthropic_key` 扩展为考虑公开池可用性
- settings_page.py 的 `_PROVIDERS` 字典新增 codex（排首位）和 openai 两个 provider，每个 entry 加 `wire` 字段标识协议类型；加公开池剩余额度 banner
- session 级额度追踪：按 token 估算 cost 累加到 `st.session_state["_pool_spend_usd"]`，超限抛 RuntimeError 引导填 Key
- commit 4af0e00 推送到 main，12 files changed，763 insertions

## 学到什么
- Streamlit `st.secrets` 在本地无 secrets.toml 时会直接 raise，必须 try/except 包裹；`os.getenv` 作为 fallback
- OpenAI SDK 异常类路径因版本不同差异大，不能直接 isinstance 判断——改为字符串级检测（检查 cls_name 和 raw_msg）更稳
- 复用 ANTHROPIC_API_KEY session_state 字段存"当前活跃 Key"（含公开池 Key）是合理设计，不需要新增字段
- 部署侧需要在 Streamlit Cloud Secrets 填三个变量：`CODEX_SHARED_KEY` / `CODEX_POOL_BUDGET_USD` / `CODEX_PER_SESSION_USD`

## 下一步
- 用户：到 navacodex.shop/register 注册兑换，将 CODEX_SHARED_KEY 填入 Streamlit Cloud Secrets
- 后续（可选）：实现 Turnstile+KV 防刷（当前公开池无防刷保护）
- 后续（可选）：月度预算统计（当前只做 session 级，无跨 session 累计）
