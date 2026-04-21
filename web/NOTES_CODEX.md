# Codex 改动日志

> 格式：`日期 | 类型(fix/refactor/test/audit) | 文件 | 一句话描述`
> Codex 每次改完代码追加一行。Claude 启动时扫最近 10 行。

---

2026-04-20 | init | CODEX.md | 建立 Codex 协作接口，定义红线和分工
2026-04-21 | audit | - | 本地 Streamlit 对抗审查报告产出，发现 8 个问题
2026-04-21 | fix | web/services/data_sync.py | 修复备份导出表枚举，避免 SQL LIKE 通配符误过滤全部业务表
2026-04-21 | fix | web/pages/jd_input.py, web/pages/master_resume.py, web/pages/settings_page.py, web/pages/resume_tailor.py | 移除审查命中的按钮和标题 emoji 文案
2026-04-21 | fix | web/pages/resume_tailor.py | 将 PDF 预览改为点击生成并按简历内容缓存，避免首次打开触发渲染
2026-04-21 | fix | web/config.py | 安全读取 Streamlit secrets，避免本地缺失 secrets.toml 时暴露绝对路径
2026-04-21 | fix | web/pages/analytics.py | 用显式 Altair 柱状图和正数数据兜底消除 Vega infinite extent 告警
