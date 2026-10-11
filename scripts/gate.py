"""게이트 판정. 조건의 원본은 docs/harness-gates.md.

사용: python scripts/gate.py <G0|G1|G2|G3|G4|S5> <실행 폴더>
종료 코드: 0 통과 · 1 미통과 · 2 컨펌 대기(G3) · 3 판정 불가(단계 불일치 등)

G3, G4, S5는 판정할 때마다 Figma REST API에서 노드를 직접 읽는다.
에이전트가 적어 둔 값으로는 판정하지 않는다.
"""
import re
import sys
from pathlib import Path

from harness_lib import (
    ROOT, SCREEN_SLUGS, STAGE_DIRS, FigmaError, adopt_items, append_summary,
    fetch_figma_page, figma_page_link, load_state, lock_hash, now, read_json,
    read_text, review_lines, save_state, sha_dir, sha_file, spec_sections,
    utf8_stdio, write_json,
)

GATES = ["G0", "G1", "G2", "G3", "G4", "S5"]
GATE_STAGE = {"G0": "G0", "G1": "S1", "G2": "S2", "G3": "S3", "G4": "S4", "S5": "S5"}
NEXT_STAGE = {"G0": "S1", "G1": "S2", "G2": "S3", "G3": "S4", "G4": "S5", "S5": "DONE"}
RETRY_LIMIT = 2      # 자동 게이트: 2회까지 다시, 3번째 미통과에 중단
S5_RETURN_LIMIT = 3  # S5→S4 복귀: 3회까지, 4번째 미통과에 중단

RULES = {
    "G0-1": "유저스토리 번호가 1개 이상이고 전부 1~5",
    "G0-2": "대상 화면명이 2개 이상이고 전부 핵심 화면 10개 안",
    "G0-3": "rules.json 해시가 design.md와 같다",
    "G0-4": "figma_file_url이 비어 있지 않다",
    "G0-5": "FIGMA_TOKEN으로 Figma 파일을 읽을 수 있다",
    "G1-1": "대상 화면마다 레퍼런스 3개 이상",
    "G1-2": "대상 화면마다 서로 다른 앱 2개 이상",
    "G1-3": "레퍼런스마다 uibowl URL 1개",
    "G1-4": "대상 화면마다 반영 항목 3~7개",
    "G1-5": "반영 항목마다 URL·스토리 번호·화면명 인용",
    "G1-6": "인용한 URL·번호·화면명이 실제로 있다",
    "G2-1": "대상 화면마다 설계서 섹션 정확히 1개",
    "G2-2": "섹션마다 입력 유저스토리 1개 이상 인용",
    "G2-3": "설계서에 인용되지 않은 반영 항목 0건",
    "G2-4": "구성 요소마다 design.md 컴포넌트명 또는 new: 표기",
    "G2-5": "키스크린 선정이 선정 규칙과 일치",
    "A-1": "공개 범위 기본 선택값이 비공개",
    "A-2": "자산 카드마다 공개 범위 표시 1개",
    "B-1": "판매 상태값이 허용 5개 안",
    "B-2": "운영자 검수 화면에 판매 기준 8개 전부",
    "B-3": "운영자 검수 액션이 승인/수정 요청/반려 정확히 3개",
    "B-4": "텍스트에 이메일·전화번호·주민번호 패턴 0건",
    "B-5": "텍스트에 금지어 0건",
    "G3-1": "키스크린 프레임 수가 선정 수와 같다",
    "G3-2": "키스크린 프레임 너비 390, 높이 844 이상",
    "G3-3": "approval.json이 있고 결과가 승인",
    "G3-4": "컨펌자 이름과 날짜가 비어 있지 않다",
    "G3-5": "반려면 사유 코드가 정확히 1개",
    "G3-6": "승인이면 Q1~Q3 답이 전부 예",
    "G4-1": "완성 시안 프레임이 대상 화면과 1:1",
    "G4-2": "tokens.json 값이 전부 rules.json에 있다",
    "G4-3": "components.json 이름이 design.md 또는 설계서 new:에 있다",
    "G4-4": "Figma 컴포넌트 인스턴스가 전부 components.json에 있다",
    "C-1": "이미지 채움을 뺀 색이 전부 색 토큰 값",
    "C-2": "액센트 색 사용 노드가 화면당 2개 이하",
    "C-3": "액센트 색이 버튼 채움에 0건",
    "T-1": "서체 패밀리가 Noto Sans KR",
    "T-2": "크기·굵기·행간 조합이 Typography 표 안",
    "T-3": "자간 0",
    "T-4": "전부 대문자 텍스트 0건",
    "R-1": "모서리 값이 0/16/24/9999 (앱 아이콘은 너비의 30%)",
    "R-2": "버튼·배지·토글 모서리 9999",
    "R-3": "드롭 섀도우 0건",
    "R-4": "기본 상태 입력 필드 테두리 0건",
    "L-1": "패딩·간격 값이 간격 토큰 안",
    "L-2": "화면 좌우 패딩 16",
    "L-3": "프레임 너비 390, 높이 844 이상",
    "L-4": "터치 대상 높이 44 이상",
    "I-1": "통과한 단계 폴더가 통과 뒤 바뀌지 않았다",
    "I-2": "docs/, rules/, scripts/가 실행 시작 뒤 바뀌지 않았다",
}
STAR = {"A-1", "A-2", "B-1", "B-2", "B-3", "B-4", "B-5"}

VISIBILITY = ["비공개", "멤버 공개", "판매 신청"]
SALE_STATES = ["임시저장", "검수 대기", "수정 요청", "승인됨", "반려"]
PHASE2_STATES = ["판매 중", "판매 중지"]
REVIEW_ACTIONS = ["승인", "수정 요청", "반려"]
REVIEW_SCREEN = "운영자 검수 화면"
ASSET_SCREENS = ("내 자산", "자산 상세")
REJECT_CODES = ["visual", "structure", "direction"]

PILL_KINDS = ("button-", "badge-", "segmented-control", "nav-pill")
TOUCH_KINDS = ("button-", "text-input", "faq-row")
PII = [
    ("이메일", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("전화번호", re.compile(r"\b0\d{1,2}[-.\s]?\d{3,4}[-.\s]?\d{4}\b")),
    ("주민번호", re.compile(r"\b\d{6}[-\s]?[1-4]\d{6}\b")),
]


def V(rule, detail, screen="", node="", actual="", allowed=""):
    return {"rule": rule, "screen": screen, "node": node,
            "actual": str(actual), "allowed": str(allowed), "detail": detail}


def label(rule):
    return ("★" if rule in STAR else "") + rule


def squash(s):
    return re.sub(r"\s+", "", s or "")


def as_list(x):
    return x if isinstance(x, list) else []


class Ctx:
    def __init__(self, run_dir, fixture=None):
        self.run = Path(run_dir)
        self.fixture = Path(fixture) if fixture else None
        ov = self.fixture / "overrides" if self.fixture else None

        def pick(name, default):
            return ov / name if ov and (ov / name).exists() else default

        self.rules_path = pick("rules.json", ROOT / "rules" / "rules.json")
        self.config_path = pick("harness.config.json", ROOT / "harness.config.json")
        self.banned_path = (ROOT / "tests" / "banned-terms.txt") if fixture else (ROOT / "rules" / "banned-terms.txt")
        self.design_path = ROOT / "docs" / "design.md"
        self.prd_path = ROOT / "docs" / "prd.md"
        self.input = read_json(self.run / "input.json", {}) or {}
        self.rules = read_json(self.rules_path, {}) or {}
        self.config = read_json(self.config_path, {}) or {}
        self.state = load_state(self.run)
        self._page = None
        self._page_tried = False
        self.figma_error = ""

    @property
    def targets(self):
        return [s for s in as_list(self.input.get("screens")) if s in SCREEN_SLUGS]

    @property
    def stories(self):
        return [s for s in as_list(self.input.get("stories")) if isinstance(s, int)]

    def figma(self):
        """Figma에서 이 실행의 페이지를 읽는다. 한 번 판정에 한 번만 읽는다."""
        if not self._page_tried:
            self._page_tried = True
            try:
                self._page = fetch_figma_page(self.config.get("figma_file_url", ""), self.run.name, self.fixture)
            except FigmaError as e:
                self.figma_error = str(e)
        return self._page

    def sections(self):
        path = self.run / STAGE_DIRS["S2"] / "screen-spec.md"
        return spec_sections(read_text(path)) if path.exists() else []

    def specs(self):
        out = {}
        for name, block in self.sections():
            out.setdefault(name, block)
        return out

    def adopt(self):
        path = self.run / STAGE_DIRS["S1"] / "adopt.md"
        return adopt_items(read_text(path)) if path.exists() else []

    def checklist(self):
        """PRD §6-7 판매 가능한 자료 기준 8개."""
        text = read_text(self.prd_path)
        m = re.search(r"판매 가능한 자료 기준:\s*\n((?:\s*\n|\d+\..*\n)+)", text)
        return re.findall(r"(?m)^\d+\.\s*(.+?)\s*$", m.group(1)) if m else []

    def banned(self):
        if not self.banned_path.exists():
            return []
        return [w.strip() for w in read_text(self.banned_path).splitlines() if w.strip() and not w.startswith("#")]


# ---------- 무결성 ----------

def check_integrity(ctx):
    v = []
    st = ctx.state
    for stage, recorded in (st.get("hashes") or {}).items():
        current = sha_dir(ctx.run / STAGE_DIRS[stage])
        if current != recorded:
            changed = sorted(set(current.items()) ^ set(recorded.items()))
            names = sorted({name for name, _ in changed})
            v.append(V("I-1", f"{STAGE_DIRS[stage]} 폴더가 통과 뒤 바뀜", actual=", ".join(names), allowed="변경 없음"))
    if st.get("lock"):
        current = lock_hash(ctx.fixture, ["lock"]) if ctx.fixture else lock_hash()
        if current != st["lock"]:
            v.append(V("I-2", "docs/, rules/, scripts/가 실행 시작 뒤 바뀜", allowed="변경 없음"))
    return v


# ---------- G0 ----------

def check_input(inp):
    """G0-1, G0-2. run.py start도 폴더를 만들기 전에 이 검사를 쓴다."""
    v = []
    stories = as_list(inp.get("stories"))
    bad = [s for s in stories if not (isinstance(s, int) and 1 <= s <= 5)]
    if not stories or bad:
        v.append(V("G0-1", "유저스토리 번호가 없거나 범위 밖", actual=bad or "없음", allowed="1~5"))
    screens = as_list(inp.get("screens"))
    bad = [s for s in screens if s not in SCREEN_SLUGS]
    if not screens or bad:
        v.append(V("G0-2", "대상 화면명이 없거나 목록 밖", actual=bad or "없음", allowed=" / ".join(SCREEN_SLUGS)))
    elif len(set(screens)) < 2:
        v.append(V("G0-2", "대상 화면이 2개 미만이라 키스크린 2~3개를 그릴 수 없음", actual=screens, allowed="서로 다른 화면 2개 이상"))
    return v


def gate_g0(ctx):
    v = check_input(ctx.input)
    if ctx.rules.get("design_sha256") != sha_file(ctx.design_path):
        v.append(V("G0-3", "rules.json이 현재 design.md와 맞지 않음. python scripts/build_rules.py로 다시 생성",
                   actual=str(ctx.rules.get("design_sha256"))[:12], allowed=sha_file(ctx.design_path)[:12]))
    if not str(ctx.config.get("figma_file_url") or "").strip():
        v.append(V("G0-4", "harness.config.json의 figma_file_url이 비어 있음"))
    elif ctx.figma() is None:
        v.append(V("G0-5", ctx.figma_error))
    return v


# ---------- G1 ----------

def gate_g1(ctx):
    v = []
    data = read_json(ctx.run / STAGE_DIRS["S1"] / "references.json", {}) or {}
    refs = [r for r in as_list(data.get("references")) if isinstance(r, dict)]
    items = ctx.adopt()
    urls = {r.get("url") for r in refs}
    for screen in ctx.targets:
        mine = [r for r in refs if r.get("screen") == screen]
        if len(mine) < 3:
            v.append(V("G1-1", "레퍼런스 부족", screen, actual=len(mine), allowed="3개 이상"))
        apps = {r.get("app") for r in mine if r.get("app")}
        if len(apps) < 2:
            v.append(V("G1-2", "서로 다른 앱 부족", screen, actual=len(apps), allowed="2개 이상"))
        n = len([i for i in items if i.get("screen") == screen])
        if not 3 <= n <= 7:
            v.append(V("G1-4", "반영 항목 수가 범위 밖", screen, actual=n, allowed="3~7개"))
    for r in refs:
        if not re.match(r"^https?://([a-z0-9-]+\.)*uibowl\.io/", str(r.get("url") or "")):
            v.append(V("G1-3", "uibowl URL이 아님", r.get("screen", ""), r.get("id", ""), r.get("url"), "https://uibowl.io/..."))
    for i in items:
        iid = i.get("id", "")
        missing = [k for k in ("ref", "story", "screen") if not i.get(k)]
        if missing:
            v.append(V("G1-5", "인용이 빠진 반영 항목", i.get("screen") or "", iid, "빠짐: " + ", ".join(missing), "ref, story, screen"))
        wrong = []
        if i.get("ref") and i["ref"] not in urls:
            wrong.append(f"ref {i['ref']}")
        if i.get("story") and i["story"] not in ctx.stories:
            wrong.append(f"story {i['story']}")
        if i.get("screen") and i["screen"] not in ctx.targets:
            wrong.append(f"screen {i['screen']}")
        if wrong:
            v.append(V("G1-6", "인용한 값이 references.json·input.json에 없음", i.get("screen") or "", iid, ", ".join(wrong)))
    return v


# ---------- G2 ----------

def comp_entries(spec):
    out = []
    for c in as_list(spec.get("components")):
        if isinstance(c, str):
            c = {"name": c}
        if isinstance(c, dict) and c.get("name"):
            out.append(c)
    return out


def comp_name(raw):
    """'new: asset-card' → ('asset-card', True)"""
    raw = str(raw).strip()
    if raw.startswith("new:"):
        return raw[4:].strip(), True
    return raw, False


def visibility_fields(spec):
    return [f for f in as_list(spec.get("fields")) if isinstance(f, dict) and "공개 범위" in str(f.get("name", ""))]


def expected_keyscreens(ctx, specs):
    """선정 규칙(docs/harness-pipeline.md)에 어긋난 점을 문장으로 돌려준다. 맞으면 ''."""
    targets, stories = ctx.targets, sorted(set(ctx.stories))
    chosen = [s for s in targets if specs.get(s, {}).get("keyscreen") is True]
    if len(targets) <= 3:
        return "" if set(chosen) == set(targets) else f"대상 화면이 3개 이하면 전부 키스크린이어야 함 (선정 {len(chosen)}/{len(targets)})"
    need = max(2, min(3, len(stories)))
    if len(chosen) != need:
        return f"키스크린 {need}개여야 함 (선정 {len(chosen)})"
    for s in stories[:3]:
        if not any(s in as_list(specs[c].get("stories")) for c in chosen):
            return f"유저스토리 {s}에 해당하는 키스크린이 없음"
    return ""


def service_checks_spec(ctx, screen, spec):
    v = []
    for f in visibility_fields(spec):
        if f.get("default") != "비공개":
            v.append(V("A-1", "공개 범위 기본값이 비공개가 아님", screen, f.get("name", ""), f.get("default"), "비공개"))
    comps = comp_entries(spec)
    cards = [c for c in comps if "asset-card" in comp_name(c["name"])[0]]
    for c in cards:
        if c.get("visibility_label") is not True:
            v.append(V("A-2", "자산 카드에 공개 범위 표시가 없음", screen, c["name"], c.get("visibility_label"), "visibility_label: true"))
    if screen in ASSET_SCREENS and not cards and not any(c.get("visibility_label") is True for c in comps):
        v.append(V("A-2", "공개 범위 표시가 있는 구성 요소가 없음", screen, allowed="visibility_label: true 1개 이상"))
    bad = [s for s in as_list(spec.get("sale_states")) if s not in SALE_STATES]
    bad += [s for s in as_list(spec.get("states")) if s in PHASE2_STATES]
    if bad:
        v.append(V("B-1", "허용되지 않은 판매 상태", screen, actual=bad, allowed=" / ".join(SALE_STATES)))
    if screen == REVIEW_SCREEN:
        have = {squash(x) for x in as_list(spec.get("checklist"))}
        missing = [c for c in ctx.checklist() if squash(c) not in have]
        if missing:
            v.append(V("B-2", "판매 기준 체크리스트 항목 누락", screen, actual="누락: " + " / ".join(missing), allowed="PRD §6-7의 8개 전부"))
        actions = as_list(spec.get("review_actions"))
        if sorted(map(str, actions)) != sorted(REVIEW_ACTIONS):
            v.append(V("B-3", "검수 액션이 3개와 다름", screen, actual=actions, allowed=" / ".join(REVIEW_ACTIONS)))
    return v


def gate_g2(ctx):
    v = []
    sections = ctx.sections()
    specs = ctx.specs()
    names = [n for n, _ in sections]
    for screen in ctx.targets:
        if names.count(screen) != 1:
            v.append(V("G2-1", "설계서 섹션 수가 1개가 아님", screen, actual=names.count(screen), allowed="1개"))
    for extra in sorted(set(names) - set(ctx.targets)):
        v.append(V("G2-1", "대상 화면이 아닌 섹션", extra, actual=extra, allowed=" / ".join(ctx.targets)))
    cited = set()
    known = set(ctx.rules.get("components") or [])
    for screen in ctx.targets:
        spec = specs.get(screen)
        if spec is None:
            continue
        if not set(as_list(spec.get("stories"))) & set(ctx.stories):
            v.append(V("G2-2", "입력한 유저스토리를 인용하지 않음", screen, actual=spec.get("stories"), allowed=ctx.stories))
        cited |= set(map(str, as_list(spec.get("adopt"))))
        for c in comp_entries(spec):
            name, is_new = comp_name(c["name"])
            if not is_new and name not in known:
                v.append(V("G2-4", "design.md에 없는 컴포넌트인데 new: 표기가 없음", screen, name, name, "design.md 컴포넌트명 또는 new:"))
        v += service_checks_spec(ctx, screen, spec)
    for i in ctx.adopt():
        if str(i.get("id")) not in cited:
            v.append(V("G2-3", "설계서에 인용되지 않은 반영 항목", i.get("screen") or "", i.get("id", "")))
    problem = expected_keyscreens(ctx, specs)
    if problem:
        v.append(V("G2-5", problem))
    return v


# ---------- Figma 노드 읽기 ----------

def walk(node, parent=None):
    if node.get("visible", True) is False:
        return
    yield node, parent
    for ch in node.get("children") or []:
        yield from walk(ch, node)


def kinds(node, page):
    """노드를 가리키는 이름들: 레이어 이름, 컴포넌트 이름, 컴포넌트 세트 이름."""
    out = {node.get("name", "")}
    comp = page["components"].get(node.get("componentId") or "")
    if comp:
        out.add(comp.get("name", ""))
        cset = page["componentSets"].get(comp.get("componentSetId") or "")
        if cset:
            out.add(cset.get("name", ""))
    return out


def instance_component(node, page):
    comp = page["components"].get(node.get("componentId") or "")
    if not comp:
        return None
    cset = page["componentSets"].get(comp.get("componentSetId") or "")
    return (cset or comp).get("name")


def starts(names, prefixes):
    return any(n.startswith(prefixes) for n in names)


def hexof(color):
    return "#%02x%02x%02x" % tuple(round(float(color.get(k, 0)) * 255) for k in "rgb")


def paint_colors(node):
    """[(hex, 'fill'|'stroke')]. 이미지 채움은 뺀다(콘텐츠가 색을 공급한다)."""
    out = []
    groups = [("fill", node.get("fills") or [])]
    if node.get("strokeWeight", 1) > 0:
        groups.append(("stroke", node.get("strokes") or []))
    for where, paints in groups:
        for p in paints:
            if p.get("visible", True) is False:
                continue
            if p.get("type") == "SOLID" and p.get("color"):
                out.append((hexof(p["color"]), where))
            elif str(p.get("type", "")).startswith("GRADIENT"):
                out += [(hexof(s["color"]), where) for s in p.get("gradientStops") or [] if s.get("color")]
    return out


def text_of(node):
    return [n.get("characters", "") for n, _ in walk(node) if n.get("type") == "TEXT"]


def named(node, name):
    return [n for n, _ in walk(node) if n.get("name") == name]


def box(node):
    return node.get("absoluteBoundingBox") or {}


def frames_with_prefix(page, prefix):
    return [(f["name"][len(prefix):], f) for f in page["frames"] if f.get("name", "").startswith(prefix)]


def check_frame_set(rule, page, prefix, expected, what):
    got = sorted(n for n, _ in frames_with_prefix(page, prefix))
    if got != sorted(expected):
        return [V(rule, f"{what} 프레임이 기대와 다름 (프레임 이름은 '{prefix}<화면명>')",
                  actual=", ".join(got) or "없음", allowed=", ".join(sorted(expected)) or "없음")]
    return []


def check_frame_size(rule, screen, frame):
    b = box(frame)
    if round(b.get("width", 0)) != 390 or b.get("height", 0) < 844:
        return [V(rule, "프레임 크기가 기준과 다름", screen, frame.get("id", ""),
                  f"{b.get('width', 0):g}×{b.get('height', 0):g}", "너비 390, 높이 844 이상")]
    return []


# ---------- G3 ----------

def gate_g3_frames(ctx):
    page = ctx.figma()
    if page is None:
        return [V("G0-5", ctx.figma_error)]
    specs = ctx.specs()
    expected = [s for s in ctx.targets if specs.get(s, {}).get("keyscreen") is True]
    v = check_frame_set("G3-1", page, "key/", expected, "키스크린")
    for name, frame in frames_with_prefix(page, "key/"):
        v += check_frame_size("G3-2", name, frame)
    return v


def check_confirm(action, name="", code="", answers=None):
    """컨펌 입력 검사. run.py confirm이 기록하기 전에 쓴다."""
    v = []
    if action == "reject":
        codes = [c for c in re.split(r"[\s,|]+", code or "") if c]
        if len(codes) != 1 or codes[0] not in REJECT_CODES:
            v.append(V("G3-5", "반려 사유 코드는 정확히 1개여야 함", actual=codes or "없음", allowed=" | ".join(REJECT_CODES)))
    else:
        if not str(name or "").strip():
            v.append(V("G3-4", "컨펌자 이름이 비어 있음"))
        answers = answers or {}
        bad = [q for q in ("Q1", "Q2", "Q3") if answers.get(q) != "예"]
        if bad:
            v.append(V("G3-6", "사람 문항이 전부 예가 아님", actual=", ".join(bad), allowed="Q1, Q2, Q3 전부 예"))
    return v


def gate_g3_approval(ctx):
    ap = read_json(ctx.run / STAGE_DIRS["S3"] / "approval.json")
    if not isinstance(ap, dict) or ap.get("result") != "승인":
        return [V("G3-3", "승인 기록이 없음", actual=(ap or {}).get("result", "approval.json 없음"), allowed="승인")]
    v = []
    if not str(ap.get("name") or "").strip() or not str(ap.get("date") or "").strip():
        v.append(V("G3-4", "컨펌자 이름 또는 날짜가 비어 있음"))
    answers = ap.get("answers") or {}
    bad = [q for q in ("Q1", "Q2", "Q3") if answers.get(q) != "예"]
    if bad:
        v.append(V("G3-6", "사람 문항이 전부 예가 아님", actual=", ".join(bad), allowed="Q1, Q2, Q3 전부 예"))
    return v


# ---------- G4 ----------

def gate_g4(ctx):
    page = ctx.figma()
    if page is None:
        return [V("G0-5", ctx.figma_error)]
    v = check_frame_set("G4-1", page, "screen/", ctx.targets, "완성 시안")
    R = ctx.rules
    tokens = read_json(ctx.run / STAGE_DIRS["S4"] / "tokens.json", {}) or {}
    allowed = {
        "colors": {str(x).lower() for x in (R.get("colors") or {}).values()},
        "spacing": set((R.get("spacing") or {}).values()),
        "rounded": set((R.get("rounded") or {}).values()),
        "typography": {(t["size"], t["weight"], t["lineHeight"]) for t in (R.get("typography") or {}).values()},
    }
    for group, values in tokens.items():
        if group not in allowed or not isinstance(values, dict):
            v.append(V("G4-2", "rules.json에 없는 토큰 그룹", node=group, actual=group, allowed=", ".join(allowed)))
            continue
        for name, val in values.items():
            if group == "typography":
                key = (val.get("size"), val.get("weight"), val.get("lineHeight")) if isinstance(val, dict) else None
            else:
                key = str(val).lower() if group == "colors" else val
            if key not in allowed[group]:
                v.append(V("G4-2", "rules.json에 없는 토큰 값", node=f"{group}.{name}", actual=val, allowed="rules.json 값"))
    data = read_json(ctx.run / STAGE_DIRS["S4"] / "components.json", {}) or {}
    listed = [str(c) for c in as_list(data.get("components"))]
    known = set(R.get("components") or [])
    for spec in ctx.specs().values():
        known |= {comp_name(c["name"])[0] for c in comp_entries(spec) if comp_name(c["name"])[1]}
    for c in listed:
        if c not in known:
            v.append(V("G4-3", "design.md에도 설계서 new:에도 없는 컴포넌트", node=c, actual=c))
    used = {}
    for name, frame in frames_with_prefix(page, "screen/"):
        for node, _ in walk(frame):
            if node.get("type") == "INSTANCE":
                comp = instance_component(node, page) or node.get("name", "")
                used.setdefault(comp, (name, node.get("id", "")))
    for comp, (screen, nid) in sorted(used.items()):
        if comp not in listed:
            v.append(V("G4-4", "components.json에 없는 컴포넌트 인스턴스", screen, nid, comp, "components.json에 등록"))
    return v


# ---------- S5 ----------

def design_checks(ctx, screen, frame, page):
    R = ctx.rules
    colors = {str(x).lower() for x in (R.get("colors") or {}).values()} | set(R.get("extra_colors") or [])
    accent = (R.get("colors") or {}).get("accent")
    typo = [(t["size"], t["weight"], t["lineHeight"]) for t in (R.get("typography") or {}).values()]
    radii = set((R.get("rounded") or {}).values())
    pill = (R.get("rounded") or {}).get("full", 9999)
    spacing = set((R.get("spacing") or {}).values()) | {0}
    family = R.get("font_family", "")
    fb = box(frame)
    width = fb.get("width", 0)

    v = check_frame_size("L-3", screen, frame)
    for ch in frame.get("children") or []:
        if ch.get("visible", True) is False:
            continue
        b = box(ch)
        x, w = b.get("x", 0) - fb.get("x", 0), b.get("width", 0)
        full_bleed = abs(x) < 0.5 and abs(w - width) < 0.5
        inside = x >= 15.5 and x + w <= width - 15.5
        if not (full_bleed or inside):
            v.append(V("L-2", "좌우 16 여백을 벗어난 요소", screen, ch.get("id", ""),
                       f"x={x:g}, 너비={w:g}", "x 16 이상·오른쪽 여백 16 이상, 또는 좌우 꽉 채움"))

    accent_nodes = []
    for node, _ in walk(frame):
        nid, ks = node.get("id", ""), kinds(node, page)
        cols = paint_colors(node)
        bad = sorted({c for c, _ in cols if c not in colors})
        if bad:
            v.append(V("C-1", "색 토큰에 없는 색", screen, nid, ", ".join(bad), "design.md 색 토큰 값"))
        if accent and any(c == accent for c, _ in cols):
            accent_nodes.append(nid)
            if starts(ks, ("button-",)) and any(c == accent and w == "fill" for c, w in cols):
                v.append(V("C-3", "액센트 색을 버튼 채움에 사용", screen, nid, accent, "버튼 채움은 primary"))

        if node.get("type") == "TEXT":
            base = node.get("style") or {}
            styles = [base] + [{**base, **o} for o in (node.get("styleOverrideTable") or {}).values()]
            fams = sorted({s.get("fontFamily", "") for s in styles} - {family})
            if fams:
                v.append(V("T-1", f"{family}가 아닌 서체. {family}를 불러오지 못해 다른 서체로 바뀐 경우도 여기에 걸린다",
                           screen, nid, ", ".join(fams), family))
            combos = set()
            for s in styles:
                size = s.get("fontSize") or 0
                ratio = round((s.get("lineHeightPx") or 0) / size, 2) if size else 0
                if not any(size == ts and s.get("fontWeight") == tw and abs(ratio - tl) <= 0.011 for ts, tw, tl in typo):
                    combos.add(f"{size:g}px/{s.get('fontWeight')}/{ratio:g}")
            if combos:
                v.append(V("T-2", "Typography 표에 없는 조합", screen, nid, ", ".join(sorted(combos)), "크기/굵기/행간 12줄 중 하나"))
            spaced = sorted({s.get("letterSpacing") or 0 for s in styles if abs(s.get("letterSpacing") or 0) > 0.01})
            if spaced:
                v.append(V("T-3", "자간이 0이 아님", screen, nid, spaced, 0))
            chars = node.get("characters", "")
            words = [w for w in chars.split() if re.fullmatch(r"[A-Za-z]+", w)]
            forced = any(s.get("textCase") in ("UPPER", "SMALL_CAPS", "SMALL_CAPS_FORCED") for s in styles)
            shouting = len(words) >= 2 and all(w.isupper() for w in words) and sum(map(len, words)) >= 8
            if forced or shouting:
                v.append(V("T-4", "전부 대문자 텍스트", screen, nid, chars[:40], "문장형 대소문자 (짧은 약어는 허용)"))

        rs = [round(r) for r in (node.get("rectangleCornerRadii") or [node.get("cornerRadius") or 0])]
        if starts(ks, ("app-icon-squircle",)):
            want = round(box(node).get("width", 0) * 0.3)
            if any(abs(r - want) > 1 for r in rs):
                v.append(V("R-1", "앱 아이콘 모서리가 너비의 30%가 아님", screen, nid, rs, want))
        elif starts(ks, PILL_KINDS):
            if any(r != pill for r in rs):
                v.append(V("R-2", "필 형태가 아닌 버튼·배지·토글", screen, nid, rs, pill))
        elif any(r not in radii for r in rs):
            v.append(V("R-1", "모서리 토큰에 없는 값", screen, nid, rs, sorted(radii)))

        shadows = [e for e in node.get("effects") or [] if e.get("type") == "DROP_SHADOW" and e.get("visible", True) is not False]
        if shadows and "segmented-control-active" not in ks:
            v.append(V("R-3", "드롭 섀도우 사용", screen, nid, len(shadows), 0))
        strokes = [p for p in node.get("strokes") or [] if p.get("visible", True) is not False]
        if "text-input" in ks and strokes and node.get("strokeWeight", 1) > 0:
            v.append(V("R-4", "기본 상태 입력 필드에 테두리", screen, nid, f"{node.get('strokeWeight', 1):g}px", "테두리 없음"))

        if node.get("layoutMode") in ("HORIZONTAL", "VERTICAL"):
            vals = {k: node.get(k, 0) for k in ("paddingLeft", "paddingRight", "paddingTop", "paddingBottom")}
            if node.get("primaryAxisAlignItems") != "SPACE_BETWEEN":
                vals["itemSpacing"] = node.get("itemSpacing", 0)
            if node.get("layoutWrap") == "WRAP":
                vals["counterAxisSpacing"] = node.get("counterAxisSpacing", 0)
            bad = {k: x for k, x in vals.items() if x not in spacing}
            if bad:
                v.append(V("L-1", "간격 토큰에 없는 값", screen, nid,
                           ", ".join(f"{k}={x:g}" for k, x in bad.items()), sorted(spacing)))
        if starts(ks, TOUCH_KINDS) and box(node).get("height", 44) < 44:
            v.append(V("L-4", "터치 대상이 44보다 낮음", screen, nid, f"{box(node).get('height'):g}", "44 이상"))

    if len(accent_nodes) > 2:
        v.append(V("C-2", "액센트 색 사용 노드가 2개 초과", screen, ", ".join(accent_nodes), len(accent_nodes), "2개 이하"))
    return v


def service_checks_figma(ctx, screen, frame, page):
    """★A·★B. 값은 전부 Figma 노드에서 읽는다. 레이어 이름 규칙은 docs/harness-roles.md."""
    v = []
    spec = ctx.specs().get(screen, {})
    selects = named(frame, "visibility-select")
    if visibility_fields(spec) and not selects:
        v.append(V("A-1", "설계서에 공개 범위 선택이 있는데 Figma에 visibility-select 레이어가 없음", screen))
    for sel in selects:
        chosen = [t.strip() for opt in named(sel, "option/selected") for t in text_of(opt)]
        if chosen != ["비공개"]:
            v.append(V("A-1", "공개 범위 기본 선택값이 비공개가 아님", screen, sel.get("id", ""), chosen or "선택 없음", "비공개"))
    cards = [n for n, _ in walk(frame) if any("asset-card" in k for k in kinds(n, page))]
    for card in cards:
        labels = [t.strip() for lab in named(card, "visibility-label") for t in text_of(lab)]
        if len(labels) != 1 or labels[0] not in VISIBILITY:
            v.append(V("A-2", "자산 카드의 공개 범위 표시가 1개가 아님", screen, card.get("id", ""), labels or "없음", " / ".join(VISIBILITY)))
    if screen in ASSET_SCREENS and not cards and not named(frame, "visibility-label"):
        v.append(V("A-2", "공개 범위 표시(visibility-label 레이어)가 없음", screen))

    status_ids = set()
    for st in named(frame, "sale-status"):
        ids = {n.get("id") for n, _ in walk(st)}
        status_ids |= ids
        value = "".join(text_of(st)).strip()
        if value not in SALE_STATES:
            v.append(V("B-1", "허용되지 않은 판매 상태", screen, st.get("id", ""), value, " / ".join(SALE_STATES)))
    texts = [(n, n.get("characters", "")) for n, _ in walk(frame) if n.get("type") == "TEXT"]
    for node, chars in texts:
        if node.get("id") not in status_ids and chars.strip() in PHASE2_STATES:
            v.append(V("B-1", "Phase 2 판매 상태가 화면에 있음", screen, node.get("id", ""), chars.strip(), " / ".join(SALE_STATES)))

    if screen == REVIEW_SCREEN:
        everything = squash("".join(c for _, c in texts))
        missing = [c for c in ctx.checklist() if squash(c) not in everything]
        if missing:
            v.append(V("B-2", "판매 기준 체크리스트 항목 누락", screen, actual="누락: " + " / ".join(missing), allowed="PRD §6-7의 8개 전부"))
        groups = named(frame, "review-actions")
        if not groups:
            v.append(V("B-3", "review-actions 레이어가 없음", screen, allowed=" / ".join(REVIEW_ACTIONS)))
        for g in groups:
            labels = ["".join(text_of(n)).strip() for n, _ in walk(g) if n is not g and starts(kinds(n, page), ("button-",))]
            if sorted(labels) != sorted(REVIEW_ACTIONS):
                v.append(V("B-3", "검수 액션이 3개와 다름", screen, g.get("id", ""), labels, " / ".join(REVIEW_ACTIONS)))

    banned = ctx.banned()
    for node, chars in texts:
        hits = [name for name, rx in PII if rx.search(chars)]
        if hits:
            v.append(V("B-4", "개인정보 패턴", screen, node.get("id", ""), f"{', '.join(hits)}: {chars[:40]}", "0건"))
        words = [w for w in banned if w in chars]
        if words:
            v.append(V("B-5", "금지어", screen, node.get("id", ""), ", ".join(words), "0건"))
    return v


def gate_s5(ctx):
    page = ctx.figma()
    if page is None:
        return [V("G0-5", ctx.figma_error)]
    v = check_frame_set("G4-1", page, "screen/", ctx.targets, "완성 시안")
    for screen, frame in frames_with_prefix(page, "screen/"):
        if screen in ctx.targets:
            v += design_checks(ctx, screen, frame, page)
            v += service_checks_figma(ctx, screen, frame, page)
    return v


# ---------- 실행 ----------

def dedupe(violations):
    seen, out = set(), []
    for x in violations:
        key = (x["rule"], x["screen"], x["node"], x["detail"], x["actual"])
        if key not in seen:
            seen.add(key)
            out.append(x)
    return out


def run_gate(ctx, gate):
    if gate == "G0":
        return gate_g0(ctx)
    if gate == "G1":
        return gate_g1(ctx)
    if gate == "G2":
        return gate_g2(ctx)
    if gate == "G3":
        return gate_g3_frames(ctx) + gate_g3_approval(ctx)
    if gate == "G4":
        return gate_g4(ctx)
    return gate_s5(ctx)


def run_all(fixture_dir):
    """테스트용. 저장된 샘플에 모든 게이트를 돌린다. 상태 파일은 건드리지 않는다."""
    ctx = Ctx(Path(fixture_dir) / "run", fixture_dir)
    v = check_integrity(ctx)
    for gate in GATES:
        v += run_gate(ctx, gate)
    return dedupe(v)


def write_report(ctx, violations, page):
    out = ctx.run / STAGE_DIRS["S5"]
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "figma-snapshot.json", page)
    write_json(out / "violations.json", {
        "run": ctx.run.name, "checked_at": now(), "source": page["source"],
        "figma_fetched_at": page["fetched_at"], "count": len(violations), "violations": violations,
    })
    lines = [f"# 검토 리포트: {ctx.run.name}", "",
             f"- 판정 시각: {now()}", f"- 데이터: Figma REST API에서 직접 읽음 ({page['fetched_at']})",
             f"- 대상 화면: {', '.join(ctx.targets)}", f"- 위반: {len(violations)}건", ""]
    if violations:
        lines += ["| 규칙 | 화면 | 노드 ID | 실제 값 | 허용 값 | 내용 |", "|---|---|---|---|---|---|"]
        for x in violations:
            cells = [label(x["rule"]), x["screen"], x["node"], x["actual"], x["allowed"], x["detail"]]
            lines.append("| " + " | ".join(str(c).replace("|", "\\|").replace("\n", " ") for c in cells) + " |")
    else:
        lines.append("위반 0건. 완료 기준을 충족했다.")
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def print_violations(gate, violations):
    for x in violations:
        where = " · ".join(p for p in (x["screen"], x["node"]) if p)
        tail = "".join([f" 실제: {x['actual']}" if x["actual"] else "", f" 허용: {x['allowed']}" if x["allowed"] else ""])
        print(f"  [{label(x['rule'])}] {x['detail']}" + (f" ({where})" if where else "") + tail)


def main(argv):
    utf8_stdio()
    if len(argv) != 3 or argv[1] not in GATES:
        print(__doc__)
        return 3
    gate, run_dir = argv[1], Path(argv[2]).resolve()
    if not (run_dir / "state.json").exists():
        print(f"실행 폴더가 아니다: {run_dir}")
        return 3
    ctx = Ctx(run_dir)
    st = ctx.state
    ok_status = st.get("status") == "running" or (gate == "G0" and st.get("status") == "halted" and st.get("stage") == "G0")
    if st.get("stage") != GATE_STAGE[gate] or not ok_status:
        print(f"판정 불가: 현재 단계 {st.get('stage')} / 상태 {st.get('status')}. {gate}는 단계 {GATE_STAGE[gate]}·상태 running에서만 돈다.")
        return 3

    integrity = check_integrity(ctx)
    if integrity:
        st["status"] = "halted"
        st["halt_reason"] = "무결성 위반"
        st.setdefault("gates", {})[gate] = {"result": "fail", "at": now(), "violations": len(integrity)}
        save_state(run_dir, st)
        append_summary(run_dir, st, "중단")
        print(f"{gate} 미통과: 무결성 위반 {len(integrity)}건. 실행을 중단한다.")
        print_violations(gate, integrity)
        return 1

    waiting = False
    if gate == "G3":
        violations = gate_g3_frames(ctx)
        if not violations:
            if (run_dir / STAGE_DIRS["S3"] / "approval.json").exists():
                violations = gate_g3_approval(ctx)
            else:
                waiting = True
    else:
        violations = run_gate(ctx, gate)
    violations = dedupe(violations)
    page = ctx._page

    # 판정에 쓴 Figma 데이터를 남긴다. 스크립트만 쓴다.
    if page and gate == "G3":
        write_json(run_dir / STAGE_DIRS["S3"] / "keyscreens.json", page)
    if page and gate == "G4":
        write_json(run_dir / STAGE_DIRS["S4"] / "screens.json", page)
    if page and gate == "S5":
        write_report(ctx, violations, page)

    gates = st.setdefault("gates", {})
    retries = st.setdefault("retries", {})
    counts = st.setdefault("violation_counts", {})

    if waiting:
        st["status"] = "waiting_confirm"
        gates["G3"] = {"result": "waiting", "at": now(), "violations": 0}
        save_state(run_dir, st)
        specs = ctx.specs()
        print("G3 컨펌 대기: 키스크린 프레임 검사 통과. 사람 컨펌이 필요하다.")
        print("  Figma:", figma_page_link(ctx.config.get("figma_file_url", ""), page.get("page_id")))
        print("  키스크린:", ", ".join(s for s in ctx.targets if specs.get(s, {}).get("keyscreen") is True))
        return 2

    if not violations:
        gates[gate] = {"result": "pass", "at": now(), "violations": 0}
        if gate in ("G1", "G2", "G3", "G4"):
            stage = GATE_STAGE[gate]
            st.setdefault("hashes", {})[stage] = sha_dir(run_dir / STAGE_DIRS[stage])
        st["stage"] = NEXT_STAGE[gate]
        st["status"] = "done" if gate == "S5" else "running"
        save_state(run_dir, st)
        print(f"{gate} 통과. 다음 단계: {st['stage']}")
        if gate == "S5":
            append_summary(run_dir, st, "완료")
            print(f"  대상 화면 {len(ctx.targets)}개 · 프레임 {len(frames_with_prefix(page, 'screen/'))}개 · 위반 0건")
            print("  Figma:", figma_page_link(ctx.config.get("figma_file_url", ""), page.get("page_id")))
            print("  리포트:", (run_dir / STAGE_DIRS["S5"] / "report.md").relative_to(ROOT).as_posix())
            print(f"  S5→S4 복귀 {st.get('s5_returns', 0)}회")
            for line in review_lines():
                print(line)
        return 0

    gates[gate] = {"result": "fail", "at": now(), "violations": len(violations)}
    for x in violations:
        counts[x["rule"]] = counts.get(x["rule"], 0) + 1
    retries[gate] = retries.get(gate, 0) + 1
    halted = False
    if gate == "G0":
        halted = True
        st["halt_reason"] = "G0 미통과"
    elif gate == "S5":
        if retries[gate] > S5_RETURN_LIMIT:
            halted = True
            st["halt_reason"] = f"S5→S4 복귀 {S5_RETURN_LIMIT}회 뒤에도 위반이 남음"
        else:
            st["s5_returns"] = retries[gate]
            st["stage"] = "S4"
            (st.get("hashes") or {}).pop("S4", None)
    elif retries[gate] > RETRY_LIMIT:
        halted = True
        st["halt_reason"] = f"{gate} 재시도 {RETRY_LIMIT}회 뒤에도 미통과"
    if halted:
        st["status"] = "halted"
    save_state(run_dir, st)
    if halted and gate != "G0":
        append_summary(run_dir, st, "중단")
    print(f"{gate} 미통과: 위반 {len(violations)}건." + (f" 실행을 중단한다 ({st['halt_reason']})." if halted else f" 단계 {st['stage']}를 다시 한다."))
    print_violations(gate, violations)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
