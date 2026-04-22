# NOTES_CLAUDE · Claude 改动日志

> Codex 启动前必读最近 10 行。
> 格式：`<时间> · claude · <ticket-id> · <状态> · <一句话>`

---

2026-04-22T23:55 · claude · HANDOFF · DONE · ticket 文档已出：`reports/ui-codex-tickets-20260422.md`（LEGACY-01 + NAV-01 + RT-01..04 串行，Landing 4 票 Appendix C 挂起）。原图裁剪在 `/tmp/img1_*.png`。
2026-04-23T00:20 · claude · VERDICT · DONE · 6 票裁决：LEGACY-01/NAV-01/RT-02/RT-03/RT-04 ✅ 过；RT-01 ❌ 不过，偏差点：toolbar 左两个控件是按钮固定 label（「简历版本 ▾」/「导出 ▾」），不是 selectbox 值显示模式。待 Codex RT-01-REV。
2026-04-23T00:30 · claude · RT-01-REV · HANDOFF · 已写入 `reports/ui-codex-tickets-20260422.md` §6.5。要求：两个触发器永远显示固定 label；推荐 `st.popover`；禁改其他 5 票范围。
2026-04-23T00:50 · claude · RT-01-REV · VERDICT · 核心逻辑过（popover + 固定 label + 0 stSelectbox），但按钮宽度 82/59 导致文字换行两行 → 新票 RT-01-REV2：加宽 column 比例，确保单行显示。
2026-04-23T01:10 · claude · RT-01-REV2 · VERDICT · ✅ 过。DOM 实测：toolbar row 高 37px 单行，按钮 144×24 / 114×24。P0 6 票全通过，可进 Landing L-1..L-4 或先归档。
