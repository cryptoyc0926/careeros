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
2026-04-21 | fix(Claude) | web/pages/settings_page.py | audit #2 API Key 和 SMTP 密码不再预填到 input DOM，改为掩码状态+留空保留
2026-04-21 | feat(Claude) | web/services/job_filter.py, scripts/clean_excluded_companies.py | audit #6 排除公司（字节/腾讯/蚂蚁/网易）过滤器+一次性清洗脚本
2026-04-21 | fix(Claude) | web/pages/{jd_browser,pipeline,job_pool,jd_input}.py | audit #6 展示层 + 导入层套用 job_filter，清洗脚本删除 jobs_pool 9 条 / job_descriptions 2 条
2026-04-21 | fix | web/app.py, web/pages/settings_page.py | 修正公开 Demo 的 Provider 文案、默认选择和云端路径展示，避免误导用户填写 Claude Key 或暴露绝对路径
2026-04-21 | fix | web/pages/resume_tailor.py | 为公开 Demo 增加占位符主简历兜底，避免在线编辑核心页出现 **** 占位标题
2026-04-21 | fix | web/pages/resume_tailor.py, web/services/resume_renderer.py | PDF 预览增加 PyMuPDF/pdf2image/iframe 三级降级，避免云端缺少 pdftoppm 时预览失败
2026-04-21 | fix | web/app.py | 清理 CSS 注释中的红线关键词，避免内联事件 grep 误报
2026-04-21 | feat(Claude) | web/services/resume_patch.py, web/services/resume_chat.py, web/pages/resume_tailor.py, requirements.txt | Chat 定制 Phase 1：JSON patch 引擎 + chat 服务(full_rewrite+advice_only) + 页面顶部对话面板 + undo 栈(10层) + PyMuPDF 依赖固化
2026-04-21 | test | web/tests/test_resume_parser.py | 加完整简历 fixture（FIXTURE_C_FULL_UPLOAD），覆盖 profile/2 项目/2 实习/技能/教育全字段校验
2026-04-21 | fix | web/services/resume_rule_parser.py | OCR 空白归一化 + inline 章节标题拆分 + 单月日期和全角破折号 + `·` 分隔 + 学校/专业 inline 拆分，修复完整简历解析丢章节
2026-04-21 | fix | web/pages/master_resume.py | 上传后自动跑规则解析 + 清 tailor_data/meta/jd/preview 缓存，避免在线定制继续用旧数据
2026-04-21 | fix | web/pages/resume_tailor.py | load_master 带 updated_at + master_signature 变化即重载 tailor_data；st.image 改 width=650 兼容旧 Streamlit
2026-04-21 | docs | web/services/resume_prompt_rules.py, CHANGELOG.md, web/prompts/resume_writing_rules.md | 规则四件套 v2.3：新增 resume_writing_rules.md（STAR/6 步法/5 槽位/动词偏好/数字规则），只同步版本号文档，未改规则常量
2026-04-21 09:10 Codex · P0-1 绑定在线编辑 widget 与 tailor_data，避免 rerun 或 chat patch 后字段丢失/旧值覆盖
2026-04-21 09:11 Codex · P0-2 覆盖 stChatInput textarea 为白底深字，修复 chat 输入框深色底
