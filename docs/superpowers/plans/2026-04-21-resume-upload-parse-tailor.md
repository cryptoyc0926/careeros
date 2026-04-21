# Resume Upload Parse Tailor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make uploaded resumes the authoritative source for `resume_master`, preserving full profile/projects/internships/skills/education and making online tailor immediately use the newly parsed resume instead of stale/demo data.

**Architecture:** Add regression fixtures for the exact full resume shape, then harden the deterministic parser and upload handoff. The parser remains pure Python and non-AI; master upload updates `master_data` plus invalidates tailor preview/session caches; `resume_tailor` reloads when `resume_master.updated_at` changes.

**Tech Stack:** Streamlit, SQLite, Python regex parser, pytest, Playwright/browser smoke checks.

---

## File Structure

- Modify `web/services/resume_rule_parser.py`: normalize PDF-extracted lines, split inline section headings, recognize three-column resume headers, preserve profile text, and parse all project/internship entries.
- Modify `web/pages/master_resume.py`: after parsing or saving a newly uploaded resume, clear stale `tailor_data`/preview state so online editing uses the new source.
- Modify `web/pages/resume_tailor.py`: track `resume_master.updated_at` and reload `tailor_data` when the DB master changes; do not apply public-demo fallback to a valid uploaded resume.
- Modify `web/tests/test_resume_parser.py`: add a full-resume regression fixture based on the uploaded complete resume.
- Append `web/NOTES_CODEX.md`: log the fix.

Do not modify `web/components/ui.py`, `.streamlit/config.toml`, or `web/services/resume_prompt_rules.py`.

---

### Task 1: Add Full Resume Parser Regression

**Files:**
- Modify: `web/tests/test_resume_parser.py`

- [ ] **Step 1: Add the failing fixture and assertions**

Append this fixture and tests to `web/tests/test_resume_parser.py`:

```python
FIXTURE_C_FULL_UPLOAD = """
杨 超
186-8795-0926 | bc1chao0926@gmail.com
求职意向：AI 产品运营实习 | 期望城市：杭州 | 到岗时间：一周内（每周可实习 5 天）

个人总结
在校期间独立运营 AI × 金融信息方向内容账号 X @Cady_btc，零投放做到 9,000+ 粉、Telegram 社群 1,300+ 订阅，完成 20+ 次品牌商单，熟悉海内外社交平台内容生态。日常用 Claude Code、Kimi、ChatGPT、Cursor 做内容生产与小工具开发。两段运营实习覆盖海外 AIGC 冷启动（TikTok / Instagram / Reddit）、竞品拆解、活动数据复盘与跨部门协作。英语 CET-6，可独立完成英文内容撰写。应用统计出身，习惯用数据面板复盘每条内容的真实表现。

项目经历
X @Cady_btc 独立运营 · AI 方向内容账号 2024.03 — 至今
• 海外社媒运营：X 推特账号自运营，主阵地面向英文受众，同步 Telegram 中文社群 1,300+ 订阅；日更 AI × 金融赛道内容，X 粉丝 0 → 9,000+，完成 20+ 次品牌商单，社区对用户反馈收集全程自理
• AI 内容生产线：基于 X API + Claude + OpenCLaw 搭建信息抓取管道，每日自动拉 50+ 条海外资讯，用 60+ 条个人 Prompt 模板筛选二次加工，单条内容生产时间从 40 分钟压到 10 分钟以内
• 达人共创：主动触达同领域博主做互推、联名推文与 Space 对谈合作，单次互推平均带来 200+ 粉增长

CareerOS（开源） 求职全流程 AI 工具 · vibe coding 作品 2026.04
• 产品定义：独立拆出 6 个核心模块（JD 抓取 / 岗位评分 / 大师简历 / 定制简历 / 公司画像 / 外联模板），端到端覆盖求职信息流；岗位池持续采集 100+ 国内外 AI 公司招聘页
• 技术实现：Streamlit + SQLite 做 Web 层，写了分级 JD 抓取管道（适配静态页、SPA、受限站点、人工录入四种来源）；大师简历 YAML + AI 定制 + 规则引擎校验三段式生成，单条 JD 定制简历 30 秒产出
• 开发方法论：全流程 vibe coding，独立完成架构设计、开发、测试、文档、部署；v0.1.0 已发布，含完整 README、架构图、Dockerfile、BYO-Key 模式
• 网站链接：careeros-chad.streamlit.app | GitHub: github.com/cryptoyc0926/careeros

实习经历
Fancy Tech 海外产品运营实习生 2024.06 — 2024.09
• 海外社媒 0 → 1：公司海外内容从零起步，独立搭建 TikTok + Instagram 官方账号，交付一套「AI 生产 — 二次编辑 — 多平台分发」SOP 文档；团队后续可复用；零投放条件下做到单条内容 10,000+ 自然曝光，带动官网均 UV 从个位数提升到 200+
• 海外竞品调研：系统拆解 PhotoRoom、Pebblely 等头部 AIGC 工具的定价策略、核心转化场景与 SEO 打法，产出 30+ 页英文竞品画像，为产品策略迭代提供输入
• 海外精准获客：在 Reddit、TikTok 垂直社群做英文私信触达与内容冷启动，拿下首批海外付费用户，验证产品 PMF 假设，建立用户反馈到内容选题的正向循环

杭银消费金融 产品运营实习生 2023.06 — 2023.10
• 活动数据复盘：搭建活动日报 + 归因模型，单场活动参与率提升 18.9%，参与人数 1,240 → 1,644，单场借款金额 1,048 万 → 1,262 万（+20.6%）
• 跨团队协作：主导业务经理朋友圈素材 SOP 升级，Canva 海报 + 文案模板化，配合产品与运营团队推进活动落地，单场触达率从 4% 提升到 10%
• 内容冷启动：策划短视频 20+ 期，账号冷启动做到单月 2w+ 播放，AB 测试确立核心激励品，投放成本下降 40%

专业技能
• AI 工具与内容生产：Claude Code、Kimi、ChatGPT、Gemini、Cursor、Perplexity、NotebookLM；Prompt 工程（模板库 60+）、Figma、Canva
• 数据、开发与语言：Python、R、MySQL、SQL、Streamlit、Git、Axure；英语 CET-6（可独立撰写英文内容）、计算机二级

教育背景
浙江工商大学 应用统计学 · 本科 2022.09 — 2026.07 | 核心课程：多元统计分析、统计预测、R 语言、贝叶斯数据分析、属性数据分析 | 荣誉：校三等奖学金、文体奖学金
""".strip()


def test_fixture_c_full_upload_preserves_all_sections():
    r = parse_resume_text(FIXTURE_C_FULL_UPLOAD)
    assert r["basics"]["name"] == "杨超"
    assert r["basics"]["phone"] == "186-8795-0926"
    assert r["basics"]["email"] == "bc1chao0926@gmail.com"
    assert r["basics"]["target_role"] == "AI 产品运营实习"
    assert r["basics"]["city"] == "杭州"
    assert "一周内" in r["basics"]["availability"]
    assert "9,000+" in r["profile"]
    assert "Claude Code" in r["profile"]
    assert len(r["projects"]) == 2
    assert r["projects"][0]["company"] == "X @Cady_btc"
    assert "独立运营" in r["projects"][0]["role"]
    assert "2024.03" in r["projects"][0]["date"]
    assert len(r["projects"][0]["bullets"]) == 3
    assert r["projects"][1]["company"].startswith("CareerOS")
    assert "2026.04" in r["projects"][1]["date"]
    assert len(r["projects"][1]["bullets"]) == 4
    assert len(r["internships"]) == 2
    assert r["internships"][0]["company"] == "Fancy Tech"
    assert r["internships"][0]["role"] == "海外产品运营实习生"
    assert "2024.06" in r["internships"][0]["date"]
    assert len(r["internships"][0]["bullets"]) == 3
    assert r["internships"][1]["company"] == "杭银消费金融"
    assert r["internships"][1]["role"] == "产品运营实习生"
    assert "2023.06" in r["internships"][1]["date"]
    assert len(r["internships"][1]["bullets"]) == 3
    assert len(r["skills"]) >= 2
    assert r["education"][0]["school"] == "浙江工商大学"
    assert "应用统计" in r["education"][0]["major"]
```

- [ ] **Step 2: Run test to verify current failure**

Run:

```bash
cd /Users/Zhuanz/Desktop/OFFER/career-os-claudecode/web
python -m pytest tests/test_resume_parser.py::test_fixture_c_full_upload_preserves_all_sections -q
```

Expected before implementation: FAIL, with profile/projects/internships/education mismatches.

- [ ] **Step 3: Commit failing test**

```bash
git add web/tests/test_resume_parser.py
git commit -m "test: cover full resume upload parsing"
```

---

### Task 2: Harden Rule Parser For Uploaded PDF Text

**Files:**
- Modify: `web/services/resume_rule_parser.py`

- [ ] **Step 1: Normalize OCR/PDF text before parsing**

Add helper functions near `_split_sections`:

```python
def _normalize_text(text: str) -> str:
    text = text.replace("\u00a0", " ").replace("\u3000", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    return text


def _explode_inline_section_headings(lines: list[str]) -> list[str]:
    out: list[str] = []
    heading_words = [kw for kws in SECTIONS.values() for kw in kws]
    heading_words.sort(key=len, reverse=True)
    heading_re = re.compile(r"(" + "|".join(re.escape(x) for x in heading_words) + r")")
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        matched = False
        for m in heading_re.finditer(line):
            before = line[:m.start()].strip()
            after = line[m.end():].strip(" :：-—–")
            if before:
                out.append(before)
            out.append(m.group(1))
            if after:
                out.append(after)
            matched = True
            break
        if not matched:
            out.append(line)
    return out
```

Change `parse_resume_text()` to call `_normalize_text(text)` and make `_split_sections()` use `_explode_inline_section_headings(text.split("\n"))`.

- [ ] **Step 2: Support single-month dates and full-width dashes**

Replace `_DATE_RANGE_RE` with:

```python
_DATE_RANGE_RE = re.compile(
    r"(\d{4}\s*[.\-/年]\s*\d{1,2}(?:\s*[.\-/月]\s*\d{0,2})?)"
    r"\s*[-~至到—–]+\s*"
    r"(\d{4}\s*[.\-/年]\s*\d{1,2}(?:\s*[.\-/月]\s*\d{0,2})?|至今|今|现在|present|now)",
    re.IGNORECASE,
)
```

- [ ] **Step 3: Parse headers with date at either end**

Inside `_parse_items`, keep the existing `date_match` branch, but after `header_text` is computed call a new helper:

```python
company, role = _split_company_role(header_text)
```

Then update `_split_company_role()` explicit separators so `·` keeps the right side as role when the left looks like a project/account name:

```python
for sep in ["|", "｜", " - ", " — ", " – ", " / "]:
    ...

if "·" in text:
    parts = [p.strip() for p in text.split("·", 1) if p.strip()]
    if len(parts) == 2:
        return parts[0], parts[1]
```

Add role keywords: `"独立运营"`, `"海外产品运营实习生"`, `"产品运营实习生"`, `"求职全流程 AI 工具"`, `"vibe coding 作品"`, `"AI 方向内容账号"`.

- [ ] **Step 4: Improve education split**

In `_parse_education`, after extracting `parts`, if the first part contains both a school and major:

```python
def _split_school_major_inline(text: str) -> tuple[str, str]:
    for kw in _SCHOOL_KEYWORDS:
        idx = text.find(kw)
        if idx >= 0:
            school = text[: idx + len(kw)].strip()
            major = text[idx + len(kw):].strip(" ·,，、:：-—–")
            return school, major
    return text, ""
```

Use it when `len(parts) == 1` or when `parts[0]` contains a school keyword and extra text.

- [ ] **Step 5: Run parser tests**

```bash
cd /Users/Zhuanz/Desktop/OFFER/career-os-claudecode/web
python -m pytest tests/test_resume_parser.py -q
```

Expected: all parser tests pass, including `test_fixture_c_full_upload_preserves_all_sections`.

- [ ] **Step 6: Commit parser fix**

```bash
git add web/services/resume_rule_parser.py web/tests/test_resume_parser.py
git commit -m "fix: preserve uploaded resume sections"
```

---

### Task 3: Make Upload Apply Reset Tailor Session State

**Files:**
- Modify: `web/pages/master_resume.py`

- [ ] **Step 1: Replace lambda `_apply_parsed` with a real helper**

Inside the upload block, replace the lambda with:

```python
def _clear_tailor_state_after_master_change() -> None:
    for key in (
        "tailor_data",
        "tailor_meta",
        "tailor_jd",
        "_tailor_preview_key",
        "_tailor_preview_pdf",
        "eval_data",
    ):
        st.session_state.pop(key, None)


def _apply_parsed(parsed: dict) -> None:
    st.session_state["master_data"] = {
        "id": (st.session_state.get("master_data") or {}).get("id"),
        "basics": parsed["basics"],
        "profile": {
            "pool": [{"id": "default", "tags": [], "text": parsed.get("profile") or ""}],
            "default": "default",
        },
        "projects": parsed.get("projects") or [],
        "internships": parsed.get("internships") or [],
        "skills": parsed.get("skills") or [],
        "education": parsed.get("education") or [],
    }
    _clear_tailor_state_after_master_change()
```

- [ ] **Step 2: Clear state after saving**

After `save_master(st.session_state.master_data)` in the top save button block, add:

```python
for key in ("tailor_data", "tailor_meta", "tailor_jd", "_tailor_preview_key", "_tailor_preview_pdf", "eval_data"):
    st.session_state.pop(key, None)
```

- [ ] **Step 3: Run syntax check**

```bash
cd /Users/Zhuanz/Desktop/OFFER/career-os-claudecode
python -m py_compile web/pages/master_resume.py
```

Expected: no output and exit code 0.

- [ ] **Step 4: Commit upload handoff fix**

```bash
git add web/pages/master_resume.py
git commit -m "fix: reset tailor state after resume upload"
```

---

### Task 4: Reload Online Tailor When Master Resume Changes

**Files:**
- Modify: `web/pages/resume_tailor.py`

- [ ] **Step 1: Return `updated_at` from `load_master()`**

Add `"updated_at": row["updated_at"]` to the dict returned by `load_master()`.

- [ ] **Step 2: Initialize/reload session data by master signature**

Replace the current `tailor_data` init with:

```python
master_signature = f"{master.get('id')}:{master.get('updated_at', '')}"
if (
    st.session_state.get("_tailor_master_signature") != master_signature
    or "tailor_data" not in st.session_state
    or (demo_fallback_active and master_needs_demo_fallback(st.session_state.tailor_data))
):
    st.session_state.tailor_data = flatten_master_for_render(master)
    st.session_state.tailor_meta = {}
    st.session_state.tailor_jd = ""
    st.session_state["_tailor_preview_key"] = None
    st.session_state["_tailor_preview_pdf"] = None
    st.session_state["_tailor_master_signature"] = master_signature
```

Keep existing defaults for `tailor_meta` and `tailor_jd` after this block for defensive compatibility.

- [ ] **Step 3: Run syntax check**

```bash
cd /Users/Zhuanz/Desktop/OFFER/career-os-claudecode
python -m py_compile web/pages/resume_tailor.py
```

Expected: no output and exit code 0.

- [ ] **Step 4: Commit tailor reload fix**

```bash
git add web/pages/resume_tailor.py
git commit -m "fix: reload tailor editor after master update"
```

---

### Task 5: Browser Regression For Upload → Parse → Save → Tailor

**Files:**
- Create: `/tmp/careeros_full_resume.md` during test only
- Modify: `web/NOTES_CODEX.md`

- [ ] **Step 1: Create a temporary Markdown resume fixture**

```bash
cat > /tmp/careeros_full_resume.md <<'EOF'
[Use the exact FIXTURE_C_FULL_UPLOAD text from Task 1]
EOF
```

- [ ] **Step 2: Run local app**

```bash
cd /Users/Zhuanz/Desktop/OFFER/career-os-claudecode
DEMO_MODE=true streamlit run web/app.py --server.port 8501 --server.headless true
```

Expected: app available at `http://localhost:8501`.

- [ ] **Step 3: Browser flow**

Use Playwright:

1. Open `http://localhost:8501/master_resume`.
2. Upload `/tmp/careeros_full_resume.md`.
3. Click `规则解析并填入字段`.
4. Verify summary includes `2 个项目 · 2 段经历`.
5. Click `保存全部`.
6. Open `http://localhost:8501/resume_tailor`.
7. Verify page contains:
   - `X @Cady_btc`
   - `CareerOS`
   - `Fancy Tech`
   - `杭银消费金融`
   - no `****`
   - no old date `2024.06 - 2024.09` mismatch if uploaded text has `2024.06 — 2024.09`
8. Click `生成预览`.
9. Verify no `预览渲染失败`.

- [ ] **Step 4: Append Codex note**

Append:

```text
2026-04-21 | fix | web/services/resume_rule_parser.py, web/pages/master_resume.py, web/pages/resume_tailor.py | 修复上传简历规则解析丢章节、在线编辑复用旧主简历和预览缓存的问题
```

- [ ] **Step 5: Commit verification note**

```bash
git add web/NOTES_CODEX.md
git commit -m "docs: log resume upload parse fix"
```

---

## Self-Review

Spec coverage:
- Uploaded full resume profile must not be blank: Task 1 + Task 2.
- Project experiences must not be blank: Task 1 + Task 2.
- Internship experiences must come from the newly uploaded resume, not stale data: Task 3 + Task 4 + Task 5.
- Missing internship count/date regression: Task 1 explicitly asserts Fancy Tech and 杭银消费金融 with dates and bullet counts.
- Online tailor must use the fresh parsed master: Task 4 and browser Task 5.

Placeholder scan:
- The only temporary placeholder is `/tmp/careeros_full_resume.md` generation in Task 5; implementation must paste the exact fixture text from Task 1.

Type consistency:
- All parser outputs match `resume_master` schema already used by `master_resume.py` and `resume_tailor.py`: `basics`, `profile`, `projects`, `internships`, `skills`, `education`.

