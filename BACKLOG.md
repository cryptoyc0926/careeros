# CareerOS Ralph Backlog

> 格式：`[ ]` 未做 / `[x]` 已做（后面跟 commit sha）
> 顺序：P0 → P1 → P2；同级按列表顺序
> 产品方向见 `RALPH_PROMPT.md` 顶部。Ralph 每轮按顺序拿第一个 `[ ]`。

---

## P0 · Bugs & 断链（优先修，阻塞 owner 主流程）

- [ ] **全站按钮/链接巡检**：用 preview_click 依次点 landing → 简历定制 → 仪表盘 → 设置页的主要按钮，console 有 error 或跳错页面的全部记下来
- [ ] **JD 输入 → 简历生成 → 仪表盘**端到端跑通一次，用 `memory/` 里已归档的蔚来 NIO 杭州校招 JD 做样本，任何一步断流的定位修复
- [ ] 简历定制页的 canvas P0 三条（pill chip / 宽度 / MD 源码透穿）如仍未收口，优先修
- [ ] AI 定制结果被硬规则拒绝的误判（若仍复现）

## P0 · 简历生成（核心模块）

- [ ] 简历定制 canvas Apple UI 终态对齐：header 不遮挡、按钮不带黑框、A4 宽度正确
- [ ] 定制结果可以下载 PDF 和 DOCX 双版本，点击后无 console error
- [ ] 主简历解析：上传 PDF 后 name/title/contact/sections 全部正确回填（往期记忆里这块有坑）
- [ ] 空项目段落占位符：如果某 section 没内容不显示空壳 card

## P1 · 仪表盘

- [ ] 看板 4 列（申请中/面试中/Offer/已关闭）计数与底层数据一致
- [ ] 点击公司卡能打开 drawer，drawer 内 JD / 简历版本 / 状态可见
- [ ] 仪表盘侧栏（mock 还是真实？）确认后接真数据或标注 mock

## P1 · UI 打磨（Apple 风克制 + 一点灵气）

- [ ] app.py 蓝框黑字按钮 → 靛蓝白按钮（L159-160 附近的硬编码）
- [ ] 数据图/指标卡的黑色 border → `BORDER_COLOR` token
- [ ] 表格黑色 border → 同上
- [ ] Sidebar 灰色字对比度过低 → `TEXT_SECONDARY`
- [ ] 首页 hero 下方冗余 block（preview 后具体定位）
- [ ] app.py 21 个 CSS hunk（Apple gray → 靛蓝白）分批提交，每轮 3-5 个 hunk
- [ ] 设置页 BYO-Key 区块的 focus ring 对齐 Apple 标准
- [ ] 所有 st.alert 再扫一遍（Round2 已统一 ~93 处，可能有漏）

## P2 · 测试覆盖

- [ ] 如项目无 `tests/` 目录，新建并写 smoke：app.py 能 import、四个 tab 能 render
- [ ] JD parser 单测：给 3 份典型 JD（飞书 SPA / LiblibAI / MiniMax）确认字段解析正确
- [ ] 简历渲染单测：给一份 fixture resume.json，渲染后 HTML 不为空、关键字段在
- [ ] 仪表盘数据查询单测：确认状态分组计数逻辑

---

## Discovered（运行中 Ralph append）

- [x] Sidebar "View more / View less" 本地化为 "查看更多 / 收起"（ralph/1）
- [ ] 主仪表盘"接下来做什么"3 个卡片（处理 P0 岗位 / 更新主简历 / 定制目标简历）的"开始 →"链接未验证是否能正常跳转
- [ ] 主仪表盘"今天的进度"第 1 张卡（岗位待处理 99）字号/布局与右侧 3 张 stat 卡（45 / 1 / 0/0）不一致，视觉割裂
- [ ] Landing 免费体验按钮（kind=primary）click 后 session 没切换到 entered_app，只有 `?app=1` URL param 才生效——候选 bug，需复现确认
- [ ] L686-695 那段 `st.markdown("<script>...")` 的 scroll reset 脚本因 Streamlit 剥离 `<script>` 而静默失效，需同迁到 components.v1.html
