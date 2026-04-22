# NOTES_CLAUDE · Claude 改动日志

> Codex 启动前必读最近 10 行。
> 格式：`<时间> · claude · <ticket-id> · <状态> · <一句话>`

---

2026-04-22T23:55 · claude · HANDOFF · DONE · ticket 文档已出：`reports/ui-codex-tickets-20260422.md`（LEGACY-01 + NAV-01 + RT-01..04 串行，Landing 4 票 Appendix C 挂起）。原图裁剪在 `/tmp/img1_*.png`。
2026-04-23T00:20 · claude · VERDICT · DONE · 6 票裁决：LEGACY-01/NAV-01/RT-02/RT-03/RT-04 ✅ 过；RT-01 ❌ 不过，偏差点：toolbar 左两个控件是按钮固定 label（「简历版本 ▾」/「导出 ▾」），不是 selectbox 值显示模式。待 Codex RT-01-REV。
2026-04-23T00:30 · claude · RT-01-REV · HANDOFF · 已写入 `reports/ui-codex-tickets-20260422.md` §6.5。要求：两个触发器永远显示固定 label；推荐 `st.popover`；禁改其他 5 票范围。
2026-04-23T00:50 · claude · RT-01-REV · VERDICT · 核心逻辑过（popover + 固定 label + 0 stSelectbox），但按钮宽度 82/59 导致文字换行两行 → 新票 RT-01-REV2：加宽 column 比例，确保单行显示。
2026-04-23T01:10 · claude · RT-01-REV2 · VERDICT · ✅ 过。DOM 实测：toolbar row 高 37px 单行，按钮 144×24 / 114×24。P0 6 票全通过，可进 Landing L-1..L-4 或先归档。
2026-04-23T02:00 · claude · COMMIT · 3 条 commit 完成（A 2bbca41 / C 13490e1 / L c9d1071），不 push。工作树剩 39 项未提（app.py CSS + Codex/Claude 历次未提）。
2026-04-23T02:30 · claude · L-1 · HANDOFF · ticket 写入 `reports/ui-codex-tickets-20260422.md` Appendix C §9。范围：仅 Hero section（`_render_topbar` + `_section_hero` + `_hero_check` + `_hero_editor_mock`）。文案/布局差异 15 处全锁，完整 OCR 副本入票。禁改其他 section + 其他文件。
2026-04-23T03:00 · claude · L-1 · VERDICT · 主干过（25/29）；4 处偏差（按钮组合/JD header/4 条 bullets/tags chip 样式），均因 ticket OCR 不准。重切 OCR 锁定后出 L-1-REV。
2026-04-23T03:20 · claude · L-1-REV · VERDICT · ✅ 过。Δ-1 按钮：个总段 AI优化/重写/⋯ 1套，项目/实习 4 段 优化/⋯ 2 件；Δ-2 JD header=岗位要求；Δ-3 4 条 bullets 新版全在；Δ-4 3 chip tags 样式白底细边框圆角 999；回归 nav/hero左/check/Fancy Tech 高亮未动。可发 L-2。
2026-04-23T03:40 · claude · L-2+L-3+L-4 · HANDOFF · 全批 ticket 写入 `reports/ui-codex-tickets-20260422.md` §9。Image 3/4/5 OCR 全锁（AI 助手面板 + diff 预览；Kanban sidebar/header/11 卡片/百度 JD/5 匹配行；BYO-Key 3 tabs + masked keys + 3 下载卡 + 版本历史 + 3 tiles）。顺序 L-2 → L-3 → L-4，一票一 commit。每票含裁剪引用、OCR、差异清单、修改范围、禁区、验收、commit msg。
2026-04-23T04:00 · claude · L-2 · VERDICT · ✅ 过。21/22 DOM 断言通过；chip/气泡/时间戳/diff 面板（红绿色值精确）/操作按钮/输入框/4 feature chip/简历 3 分组齐全；L-1 回归零破坏（Fancy Tech 蓝高亮 + L-1 按钮计数完全不变）。唯一小偏差：用户气泡「突出 AI」之间用 `<br>` 替代空格（视觉同原图换行，不影响像素；下次提醒 Codex 用纯空格让文本自然流）。可 commit C-L2 并进 L-3。
2026-04-23T04:30 · claude · L-3 · VERDICT · ✅ 过。pill + title + 副标 + kanban header + 4 列计数 + 11 公司 + 10 sidebar 项 + drawer（4 tabs + 93% + 5 matches + 编辑 JD/去投递）+ 4 底部更多链接全过。Forbidden 3 命中全是 false positive（L-1/L-2/L-4 旧残留词在其他 section，非 L-3 问题）。回归：L-1 nav/hero/按钮 + L-2 chip/ts/diff/feature chips 完好；3 Fancy Tech 高亮色值锁死。可 commit C-L3 并进 L-4。
2026-04-23T05:00 · claude · L-4 · VERDICT · ✅ 过。全部 40+ 断言通过：2 标题 chips + 副标 + 3 tabs + 模型服务标题 + 4 masked keys (sk-ant/proj/codex/kimi) + 添加自定义模型 + 数据安全与隐私 + 本地优先·端到端加密 chip + 3 下载卡（原稿/原稿改写/模板版）+ 版本历史 4 行 + 当前版本 chip + 4 时间戳 + 3 value tiles 文案全锁。Grid 实测 381×3 列。Forbidden 0（含旧 4 tile/tabs/未测试/随时切换/一键切换 全清）。L-1/L-2/L-3 回归完好。Landing 4 section 全部 1:1 对齐 Image 2-5 完成。
