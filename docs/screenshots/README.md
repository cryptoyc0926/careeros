# 截图库

本目录存放 README 中引用的截图。已发布 v0.1.0 清单：

- [x] `home.png` — 首页（hero + 今日进度 + 任务卡）
- [x] `master_resume.png` — 主简历编辑页（7 tab）
- [x] `jd_input.png` — JD 添加页（4 种入口）
- [x] `resume_tailor.png` — 在线定制 3 栏布局（JD + 编辑 + 实时预览）
- [x] `pipeline.png` — 投递看板（6 状态列 + 终态）
- [x] `analytics.png` — 数据分析（soft_stat_card + 漏斗 + 分布）

## 抓取方法（留给维护者）

全部图均为 1600×900 viewport · device_scale_factor=2 下的 Playwright 截图，约 3200×1800。主简历和在线定制两页使用 **演示数据库**（Demo User / 138-0000-0000 / demo@example.com）抓取，避免泄露个人隐私。重跑方式见 `scripts/` 下的相关说明，或参考 CONTRIBUTING.md。

## 截图规范

- 分辨率：1600×900 或更高
- 格式：PNG（avoid JPEG 失真）
- 隐私：截图前切换到 `data/user_profile.example.yaml` 的占位画像，不要露出你的真实姓名/学校/邮箱
- 命名：全小写 + 下划线，匹配上方清单

## 建议工具

- macOS：`Cmd + Shift + 4` → 空格 → 点击窗口
- Chrome DevTools：设备模拟 1600x900 → 截屏
