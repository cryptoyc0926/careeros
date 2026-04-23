# Ralph Loop · CareerOS (career-os-claudecode)

你在一个 Ralph loop 里。**每轮做一件中等改进**（一个页面 / 一个组件 / 一个完整子流程）、验证、提交、更新日志，然后决定下一轮何时起。

---

## 产品方向（不要忘）

- **核心目标**：做成可以录屏演示的 demo，同时真能帮 owner 找到工作。
- **主要用户**：owner 本人（杨超），日常高频使用。
- **主工作流**：上传/粘贴 JD → 生成定制简历 → 在仪表盘看进度。
- **优先模块**：**简历生成 > 仪表盘 > JD 输入**（JD 输入仅在阻塞简历生成时才修）。
- **主攻问题**：
  1. 按钮/链接失效、跳错、真实交互 bug
  2. UI 未达到 Apple 风格克制 + 一点产品经理灵气的品质
  3. 可用性差
  4. 测试覆盖缺失
- **迭代优先级**：① 明显 bug 和断链 → ② Apple 风格专业克制的 UI → ③ 保护工作流的测试
- **允许**：合理的 layout 重构（验证通过就行）；必要的新依赖（写明理由）；付费 API 调用做真实验证（每轮 ≤ 2 次，不浪费）。
- **文案改动**：小而清晰，不扩写。

---

## 硬约束（不能违反）

1. 工作目录只能是 `/Users/Zhuanz/Desktop/OFFER/career-os-claudecode/`。
2. 只能改 `web/`、`prompts/`、`tests/`（如存在）、`memory/` 下的文件。禁改 `scripts/`、`data/`、`linkedin/`、`logs/`、`Dockerfile`、`requirements.txt`（除非是"加新依赖"且写明理由）。
3. 不准 `git push`、不准 `git push --force`、不准 `git reset --hard`、不准 `git commit --no-verify`、不准改 `git config`、不准动 `.git/`。
4. 每轮最多改 **5 个文件**，最多加 **1 个新依赖**。
5. 付费 API 调用每轮 ≤ 2 次（用户的 navacodex.shop 共享池）。
6. 禁止 `kill` 用户的 streamlit / 任何 dev server 进程。
7. 如果验证失败且一次重试还失败 → `git checkout -- <改过的文件>` 回滚本轮改动，LOOP_LOG 记 FAIL，本轮结束。
8. 破坏性 / 需要数据迁移或删除 / 外部账号或安全决策 / 超出本产品方向的重大产品决策 → **停下来写 LOOP_LOG 等用户**，本轮不继续。

---

## 每轮标准流程（9 步）

### Step 1 · Pre-flight

- `cd /Users/Zhuanz/Desktop/OFFER/career-os-claudecode`
- `git status --short`：
  - 如果全部已跟踪文件都是 clean → OK。
  - 如果有 *modified* 的已跟踪文件但本轮还没动手 → 这是用户 WIP 或上一轮漏提交，**停下写 LOOP_LOG 等用户**。
  - 如果只有 *untracked*（`??`）文件 → 忽略，不挡路。
- `git log --oneline -5` 扫最近 5 条 commit，确保上一轮的 `ralph/N:` 在。
- `tail -10 LOOP_LOG.md` 读近 10 行，不要撞车。

### Step 2 · 选任务

顺序：
1. **BACKLOG.md 里第一个 `[ ]`**（按 P0 → P1 → P2 排列，优先级内顺序执行）。
2. 如果 BACKLOG 全 done → **自主探索**（见下）。
3. 如果有 failing test / console error → 无条件优先修（插到最前）。

任务范围：一个页面 or 一个组件 or 一个完整子流程。不选"全站重构"这种大锤。

### Step 3 · 读源码

- 读目标文件 + 1-2 个相关文件
- 优先找现有 component / token / helper 复用，不造新抽象
- 确认当前行为是 bug 还是"只是丑"

### Step 4 · 改代码

- 最多 5 个文件
- 保留用户已有编辑、保留无关文件
- 改动尽量内聚，不搞顺手大清理

### Step 5 · 自测核心工作流（关键 — 不要跳）

这是 **Ralph loop 的灵魂**：每轮亲自跑一遍 owner 的主流程，别只信静态检查。

- **简历生成/仪表盘改动** → 至少用 **3 份 JD 样本 + 2 份简历 variant** 跑端到端：
  - JD 输入/上传 → 定制简历生成 → 仪表盘能看到结果
- **其他页面改动** → preview 截图 + 点一次该页面的主要按钮
- 没有现成 JD/简历样本时，从 `data/` 或 `memory/` 里找已有的，不要自己编

具体动作：
- `python -m py_compile <改过的.py>`
- `preview_start`（如未跑）
- 用 `preview_click` / `preview_fill` 做一遍主路径
- `preview_console_logs` 看 error
- `preview_screenshot` 存到 `/tmp/ralph_<N>_<task>.png`
- `preview_snapshot` 确认 DOM

### Step 6 · 跑测试

- **首选**：`cd /Users/Zhuanz/Desktop/OFFER/career-os-claudecode && source venv/bin/activate 2>/dev/null || source ../career-os/venv/bin/activate && python -m pytest -q` （本项目无 venv 就借用 career-os 的）
- **宽工作流改动**：另跑 `python tests/run_e2e_test.py`（如存在）
- 没 test 可跑 → 明确在 LOOP_LOG 标 `NO_TESTS`，不装作"通过"

### Step 7 · 裁决 + 提交

- 所有验证通过 → `git add <改过的文件>` + `git commit -m "ralph/<N>: <task 一句话>"`
- 任何一项失败 → 允许一次小修 + 重跑 step 5-6；还是失败 → `git checkout -- <file>` 全部回滚
- **永远不 push**

### Step 8 · 更新 BACKLOG + LOOP_LOG

- BACKLOG.md：完成项 `[ ]` → `[x]` + 追加 commit sha；发现的新问题 append 到 **Discovered** 段
- LOOP_LOG.md：append 一行
  ```
  <N> | YYYY-MM-DD HH:MM | PASS/FAIL/NO_TESTS | <task 简述> | <commit sha or rollback> | <screenshot path>
  ```

### Step 9 · 决定下一轮

- BACKLOG 还有 `[ ]` + 没撞硬约束 + dev server 健康 → 调用 `ScheduleWakeup`，`delaySeconds` 在 60-300 之间，`prompt` 传回当前 /loop 输入原文，`reason` 写明"下一轮要攻哪个 backlog 项"
- 连续 2 轮在"自主探索"模式找不到可改项 → LOOP_LOG 标 `backlog exhausted`，不调用 ScheduleWakeup，循环自然结束
- 撞到 Step 1 / Step 7 的停机条件 → 不调用 ScheduleWakeup，等用户

---

## 自主探索模式（BACKLOG 空时）

1. `preview_screenshot` 截以下页面：landing / app.py 四个 tab / 简历定制 / 仪表盘 / 设置页
2. 对照 `CLAUDE.md` 里的 Apple UI 规范 + `memory/` 最近的设计 token 归档
3. 找 **一条具体违规**（禁用"整站感觉不够好"这种虚描述），写进 BACKLOG.md 的 Discovered 段
4. 回到正常流程 Step 3

---

## 每轮对话输出（严格）

- **≤ 3 句话**，每句信息密度高
- 模板：`轮次 N | 改了 <task> | 验证 PASS/FAIL | 下一轮 <next target>`
- 不要寒暄、不要重复 BACKLOG 原文、不要贴 diff（commit 里已有）

---

## 启动这条 loop 的方式（用户睡前敲）

```
/loop 读取 /Users/Zhuanz/Desktop/OFFER/career-os-claudecode/RALPH_PROMPT.md 的完整内容，按其中"每轮标准流程"执行一轮。本轮结束后如果满足继续条件，用 ScheduleWakeup 自动触发下一轮。
```

不带时间参数 = 自主节奏。

---

## 早上看什么

1. `cat /Users/Zhuanz/Desktop/OFFER/career-os-claudecode/LOOP_LOG.md` — 整夜轨迹
2. `cd /Users/Zhuanz/Desktop/OFFER/career-os-claudecode && git log --oneline` — commit 列表
3. 想留的 commit 保留；不想要的 `git reset <sha>~1` 扔回工作区
4. 挑确认好的 `git push`
