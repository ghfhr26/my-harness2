"""tests/pass, tests/fail 샘플을 만든다.

- tests/pass/            모든 게이트를 통과하는 정상 세트 1개
- tests/fail/<규칙 ID>/  그 규칙 하나만 어긴 샘플. 같은 규칙에 여러 개면 <규칙 ID>--<설명>

샘플의 figma/ 폴더는 Figma REST API 응답과 같은 모양이다.
scripts/test_gates.py가 매번 이 스크립트를 먼저 돌려 샘플을 현재 design.md 기준으로 맞춘다.
"""
import copy
import itertools
import json
import shutil
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))

import gate as G  # noqa: E402
from harness_lib import ROOT, STAGE_DIRS, lock_hash, read_json, sha_dir, write_json  # noqa: E402

RULES = read_json(ROOT / "rules" / "rules.json")
COLOR = RULES["colors"]
TYPO = RULES["typography"]
WEIGHT_NAME = {300: "Light", 400: "Regular", 500: "Medium", 700: "Bold"}
SCREENS = ["내 자산", "운영자 검수 화면"]
APPS = ["토스", "당근", "Notion"]
_ids = itertools.count(10)


def nid():
    return f"1:{next(_ids)}"


def solid(hexcode):
    r, g, b = (int(hexcode[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return {"blendMode": "NORMAL", "type": "SOLID", "color": {"r": r, "g": g, "b": b, "a": 1}}


def rect(x, y, w, h):
    return {"x": x, "y": y, "width": w, "height": h}


def text(chars, token, x, y, w, color=None, name=None):
    t = TYPO[token]
    return {
        "id": nid(), "name": name or chars, "type": "TEXT", "characters": chars,
        "absoluteBoundingBox": rect(x, y, w, round(t["size"] * t["lineHeight"], 2)),
        "fills": [solid(color or COLOR["ink"])],
        "style": {
            "fontFamily": "Noto Sans KR", "fontPostScriptName": f"Noto Sans KR-{WEIGHT_NAME[t['weight']]}",
            "fontWeight": t["weight"], "fontSize": t["size"],
            "lineHeightPx": t["size"] * t["lineHeight"], "lineHeightUnit": "PIXELS", "letterSpacing": 0,
        },
    }


def frame(name, x, y, w, h, children=(), fill=None, radius=0, layout=None, pad=(0, 0, 0, 0), gap=0,
          stroke=None, kind="FRAME", component=None):
    node = {
        "id": nid(), "name": name, "type": kind, "absoluteBoundingBox": rect(x, y, w, h),
        "fills": [solid(fill)] if fill else [], "strokes": [], "effects": [], "children": list(children),
    }
    if radius:
        node["cornerRadius"] = radius
    if layout:
        node.update(layoutMode=layout, paddingLeft=pad[0], paddingRight=pad[1], paddingTop=pad[2],
                    paddingBottom=pad[3], itemSpacing=gap)
    if stroke:
        node.update(strokes=[solid(stroke)], strokeWeight=1)
    if component:
        node.update(type="INSTANCE", componentId=component)
    return node


def button(comp, label, x, y, w, primary=True):
    return frame(
        "button-primary" if primary else "button-outline", x, y, w, 48,
        [text(label, "link", x + 16, y + 12, w - 32, COLOR["on-primary"] if primary else COLOR["ink"])],
        fill=COLOR["primary"] if primary else COLOR["canvas"], radius=9999, layout="HORIZONTAL",
        pad=(16, 16, 0, 0), stroke=None if primary else COLOR["hairline"], component=comp,
    )


def build_figma(checklist):
    """Figma REST API 응답 모양의 (file, nodes)."""
    global _ids
    _ids = itertools.count(10)
    frames = []
    for i, screen in enumerate(SCREENS):
        frames.append(frame(f"key/{screen}", i * 500, 0, 390, 844, fill=COLOR["canvas"]))

    fx = 1000
    option_on = frame("option/selected", fx + 20, 124, 173, 40, [text("비공개", "link", fx + 36, 133, 141)],
                      fill=COLOR["canvas"], radius=9999, layout="HORIZONTAL", pad=(16, 16, 0, 0))
    option_off = frame("option", fx + 197, 124, 173, 40,
                       [text("멤버 공개", "link", fx + 213, 133, 141, COLOR["text-muted"])],
                       radius=9999, layout="HORIZONTAL", pad=(16, 16, 0, 0))
    card = frame("asset-card", fx + 16, 248, 358, 140, [
        text("회의록 요약 프롬프트", "title", fx + 40, 272, 310),
        text("비공개", "label", fx + 40, 304, 310, COLOR["text-muted"], name="visibility-label"),
        text("검수 대기", "caption", fx + 40, 329, 310, COLOR["text-muted"], name="sale-status"),
    ], fill=COLOR["canvas"], radius=24, layout="VERTICAL", pad=(24, 24, 24, 24), gap=8,
        stroke=COLOR["hairline-soft"], component="c1")
    frames.append(frame("screen/내 자산", fx, 0, 390, 844, [
        text("내 자산", "heading-1", fx + 16, 64, 358, name="title"),
        frame("visibility-select", fx + 16, 120, 358, 48, [option_on, option_off], fill=COLOR["canvas-soft"],
              radius=9999, layout="HORIZONTAL", pad=(4, 4, 4, 4), gap=4),
        frame("text-input", fx + 16, 184, 358, 48,
              [text("자산 검색", "body", fx + 32, 196, 326, COLOR["text-faint"])],
              fill=COLOR["field"], radius=16, layout="HORIZONTAL", pad=(16, 16, 12, 12), component="c5"),
        card,
        button("c2", "새 자산 등록", fx + 16, 420, 358),
    ], fill=COLOR["canvas"]))

    fx = 1500
    rows = [text(c, "body", fx + 40, 164 + n * 34, 310) for n, c in enumerate(checklist)]
    frames.append(frame("screen/운영자 검수 화면", fx, 0, 390, 844, [
        text("판매 신청 검수", "heading-1", fx + 16, 64, 358, name="title"),
        text("검수 대기", "caption", fx + 16, 112, 358, COLOR["text-muted"], name="sale-status"),
        frame("review-checklist", fx + 16, 140, 358, 330, rows, fill=COLOR["canvas-soft"], radius=24,
              layout="VERTICAL", pad=(24, 24, 24, 24), gap=12, component="c3"),
        frame("review-actions", fx + 16, 494, 358, 48, [
            button("c2", "승인", fx + 16, 494, 114),
            button("c4", "수정 요청", fx + 138, 494, 114, primary=False),
            button("c4", "반려", fx + 260, 494, 114, primary=False),
        ], layout="HORIZONTAL", gap=8),
    ], fill=COLOR["canvas"]))

    file_doc = {"name": "fixture", "document": {"id": "0:0", "type": "DOCUMENT", "children": [
        {"id": "0:1", "name": "run", "type": "CANVAS"}]}}
    nodes_doc = {"nodes": {"0:1": {
        "document": {"id": "0:1", "name": "run", "type": "CANVAS", "children": frames},
        "components": {
            "c1": {"key": "k1", "name": "asset-card"}, "c2": {"key": "k2", "name": "button-primary"},
            "c3": {"key": "k3", "name": "review-checklist"}, "c4": {"key": "k4", "name": "button-outline"},
            "c5": {"key": "k5", "name": "text-input"},
        },
        "componentSets": {},
    }}}
    return file_doc, nodes_doc


def build_base():
    checklist = G.Ctx(HERE, HERE).checklist()
    assert len(checklist) == 8, "PRD §6-7 판매 기준 8개를 읽지 못했다"
    refs, items = [], []
    for s, screen in enumerate(SCREENS):
        for n in range(3):
            k = s * 3 + n + 1
            refs.append({"id": f"R-{k:02d}", "screen": screen, "app": APPS[n], "url": f"https://uibowl.io/ui/{k}"})
        for n in range(3):
            k = s * 3 + n + 1
            items.append({"id": f"A-{k:02d}", "ref": f"https://uibowl.io/ui/{s * 3 + (n % 2) + 1}",
                          "story": 4 if s == 0 else 5, "screen": screen, "text": f"반영 내용 {k}"})
    spec = [
        ["내 자산", {
            "screen": "내 자산", "stories": [4], "adopt": ["A-01", "A-02", "A-03"], "keyscreen": True,
            "components": [{"name": "button-primary"}, {"name": "text-input"},
                           {"name": "new: asset-card", "visibility_label": True}],
            "fields": [{"name": "공개 범위", "options": list(G.VISIBILITY), "default": "비공개"}],
            "sale_states": ["임시저장", "검수 대기", "승인됨"], "actions": ["새 자산 등록"],
        }],
        ["운영자 검수 화면", {
            "screen": "운영자 검수 화면", "stories": [5], "adopt": ["A-04", "A-05", "A-06"], "keyscreen": True,
            "components": [{"name": "button-primary"}, {"name": "button-outline"}, {"name": "new: review-checklist"}],
            "checklist": list(checklist), "review_actions": list(G.REVIEW_ACTIONS), "sale_states": ["검수 대기"],
        }],
    ]
    file_doc, nodes_doc = build_figma(checklist)
    return {
        "input": {"screens": list(SCREENS), "stories": [4, 5], "created": "2026-10-11T10:00:00"},
        "references": refs, "adopt": items, "spec": spec,
        "approval": {"result": "승인", "code": None, "name": "김관계", "date": "2026-10-11T12:00:00",
                     "answers": {"Q1": "예", "Q2": "예", "Q3": "예"}, "memo": ""},
        "tokens": {"colors": {"ink": COLOR["ink"], "canvas": COLOR["canvas"]}, "spacing": {"md": 16},
                   "rounded": {"md": 24}, "typography": {"body": {"size": 15, "weight": 400, "lineHeight": 1.5}}},
        "components": ["asset-card", "button-primary", "review-checklist", "button-outline", "text-input"],
        "figma_file": file_doc, "figma_nodes": nodes_doc,
        "overrides": {"harness.config.json": {"figma_file_url": "https://www.figma.com/design/FIXTUREKEY/huddling"}},
        "post": None, "confirm": None,
    }


def write_fixture(path, S):
    shutil.rmtree(path, ignore_errors=True)
    path.mkdir(parents=True)
    if S["confirm"]:
        write_json(path / "confirm.json", S["confirm"])
        return
    run = path / "run"
    for d in STAGE_DIRS.values():
        (run / d).mkdir(parents=True)
    write_json(run / "input.json", S["input"])
    write_json(run / "s1-reference" / "references.json", {"references": S["references"]})
    adopt = "# 반영 항목\n\n```yaml\n" + yaml.safe_dump({"items": S["adopt"]}, allow_unicode=True, sort_keys=False) + "```\n"
    (run / "s1-reference" / "adopt.md").write_text(adopt, encoding="utf-8")
    spec = "# 화면설계서\n"
    for name, block in S["spec"]:
        spec += f"\n## {name}\n\n```yaml\n" + yaml.safe_dump(block, allow_unicode=True, sort_keys=False) + "```\n\n레이아웃과 흐름 설명.\n"
    (run / "s2-spec" / "screen-spec.md").write_text(spec, encoding="utf-8")
    if S["approval"] is not None:
        write_json(run / "s3-keyscreen" / "approval.json", S["approval"])
    write_json(run / "s4-build" / "tokens.json", S["tokens"])
    write_json(run / "s4-build" / "components.json", {"components": S["components"]})
    if S["figma_file"] is not None:
        write_json(path / "figma" / "file.json", S["figma_file"])
        write_json(path / "figma" / "nodes.json", S["figma_nodes"])
    for name, data in S["overrides"].items():
        write_json(path / "overrides" / name, data)
    (path / "lock").mkdir()
    (path / "lock" / "lock.txt").write_text("docs/rules/scripts 대역\n", encoding="utf-8")
    write_json(run / "state.json", {
        "run": "run", "created": "2026-10-11T10:00:00", "stage": "S5", "status": "running",
        "gates": {}, "retries": {}, "s5_returns": 0, "violation_counts": {}, "confirm_history": [],
        "hashes": {s: sha_dir(run / STAGE_DIRS[s]) for s in ("S1", "S2", "S3", "S4")},
        "lock": lock_hash(path, ["lock"]),
    })
    if S["post"]:
        S["post"](path)


# ---------- 샘플 안에서 노드 찾기 ----------

def frames_of(S):
    return S["figma_nodes"]["nodes"]["0:1"]["document"]["children"]


def get_frame(S, name):
    return next(f for f in frames_of(S) if f["name"] == name)


def drop_frame(S, name):
    frames_of(S)[:] = [f for f in frames_of(S) if f["name"] != name]


def find(node, name):
    if node.get("name") == name:
        return node
    for ch in node.get("children") or []:
        hit = find(ch, name)
        if hit:
            return hit
    return None


def node(S, frame_name, name):
    return find(get_frame(S, frame_name), name)


MINE, REVIEW = "screen/내 자산", "screen/운영자 검수 화면"


def spec_of(S, screen):
    return next(b for n, b in S["spec"] if n == screen)


def adopt_of(S, item_id):
    return next(i for i in S["adopt"] if i["id"] == item_id)


# ---------- 규칙별 위반 ----------

def m_g0_3(S):
    S["overrides"]["rules.json"] = {**RULES, "design_sha256": "0" * 64}


def m_g0_2_single(S):
    # 대상 화면을 1개만 넣은 실행. 나머지 산출물은 그 1개에 맞게 줄여 G0-2만 걸리게 한다.
    S["input"].update(screens=["내 자산"], stories=[4])
    S["references"][:] = [r for r in S["references"] if r["screen"] == "내 자산"]
    S["adopt"][:] = [i for i in S["adopt"] if i["screen"] == "내 자산"]
    S["spec"][:] = [s for s in S["spec"] if s[0] == "내 자산"]
    S["components"][:] = ["asset-card", "button-primary", "text-input"]
    drop_frame(S, "key/운영자 검수 화면")
    drop_frame(S, REVIEW)


def m_g2_5(S):
    spec_of(S, "운영자 검수 화면")["keyscreen"] = False
    drop_frame(S, "key/운영자 검수 화면")


def m_a1_figma(S):
    sel = node(S, MINE, "visibility-select")
    sel["children"][0]["children"][0]["characters"] = "멤버 공개"
    sel["children"][1]["children"][0]["characters"] = "비공개"


def m_b3_figma(S):
    acts = node(S, REVIEW, "review-actions")
    acts["children"].append(button("c4", "허들링 픽 선정", 1516, 494, 114, primary=False))


def m_c2(S):
    for n in range(3):
        get_frame(S, MINE)["children"].append(
            frame("dot", 1016 + n * 24, 500, 16, 16, fill=COLOR["accent"]))


def m_t1_fallback(S):
    # Noto Sans KR를 불러오지 못해 Figma 기본 서체로 바뀐 경우
    n = find_all_text(node(S, MINE, "asset-card"))[0]
    n["style"].update(fontFamily="Inter", fontPostScriptName="Inter-" + n["style"]["fontPostScriptName"].split("-")[1])


def find_all_text(n):
    out = [n] if n.get("type") == "TEXT" else []
    for ch in n.get("children") or []:
        out += find_all_text(ch)
    return out


def m_t2(S):
    t = node(S, REVIEW, "review-checklist")["children"][0]
    t["style"].update(fontSize=14, lineHeightPx=21)


def m_r3(S):
    node(S, MINE, "asset-card")["effects"] = [{"type": "DROP_SHADOW", "visible": True, "radius": 8,
                                                "color": {"r": 0, "g": 0, "b": 0, "a": 0.1}, "offset": {"x": 0, "y": 2}}]


def m_r4(S):
    node(S, MINE, "text-input").update(strokes=[solid(COLOR["hairline"])], strokeWeight=1)


def post_i1(path):
    with (path / "run" / "s1-reference" / "adopt.md").open("a", encoding="utf-8") as f:
        f.write("\n통과 뒤에 덧붙인 줄.\n")


def post_i2(path):
    (path / "lock" / "lock.txt").write_text("실행 시작 뒤 바뀐 내용\n", encoding="utf-8")


FAILS = {
    "G0-1": lambda S: S["input"]["stories"].append(9),
    "G0-2": lambda S: S["input"]["screens"].append("설정"),
    "G0-2--single-screen": m_g0_2_single,
    "G0-3": m_g0_3,
    "G0-4": lambda S: S["overrides"].update({"harness.config.json": {"figma_file_url": ""}}),
    "G0-5": lambda S: S.update(figma_file=None),
    "G1-1": lambda S: S["references"].pop(2),
    "G1-2": lambda S: [r.update(app="토스") for r in S["references"][:3]],
    "G1-3": lambda S: S["references"][2].update(url="https://example.com/ui/3"),
    "G1-4": lambda S: S["adopt"].pop(2),
    "G1-5": lambda S: adopt_of(S, "A-03").update(ref=""),
    "G1-6": lambda S: adopt_of(S, "A-03").update(ref="https://uibowl.io/ui/999"),
    "G2-1": lambda S: S["spec"].append(copy.deepcopy(S["spec"][0])),
    "G2-2": lambda S: spec_of(S, "내 자산").update(stories=[1]),
    "G2-3": lambda S: spec_of(S, "내 자산").update(adopt=["A-01", "A-02"]),
    "G2-4": lambda S: spec_of(S, "내 자산")["components"].append({"name": "fancy-widget"}),
    "G2-5": m_g2_5,
    "A-1": lambda S: spec_of(S, "내 자산")["fields"][0].update(default="멤버 공개"),
    "A-1--figma": m_a1_figma,
    "A-1--figma-missing": lambda S: node(S, MINE, "visibility-select").update(name="select"),
    "A-2": lambda S: spec_of(S, "내 자산")["components"][2].update(visibility_label=False),
    "A-2--figma": lambda S: node(S, MINE, "visibility-label").update(name="label"),
    "B-1": lambda S: spec_of(S, "내 자산")["sale_states"].append("판매 중"),
    "B-1--figma": lambda S: node(S, MINE, "sale-status").update(characters="판매 중"),
    "B-2": lambda S: spec_of(S, "운영자 검수 화면")["checklist"].pop(),
    "B-2--figma": lambda S: node(S, REVIEW, "review-checklist")["children"].pop(),
    "B-3": lambda S: spec_of(S, "운영자 검수 화면")["review_actions"].append("허들링 픽 선정"),
    "B-3--figma": m_b3_figma,
    "B-4": lambda S: node(S, MINE, "title").update(characters="문의 hello@huddling.ai"),
    "B-4--phone": lambda S: node(S, MINE, "title").update(characters="문의 010-1234-5678"),
    "B-5": lambda S: node(S, MINE, "title").update(characters="카카오뱅크 자산"),
    "G3-1": lambda S: drop_frame(S, "key/운영자 검수 화면"),
    "G3-2": lambda S: get_frame(S, "key/내 자산")["absoluteBoundingBox"].update(height=800),
    "G3-3": lambda S: S["approval"].update(result="반려", code="visual"),
    "G3-4": lambda S: S["approval"].update(name=""),
    "G3-5": lambda S: S.update(confirm={"action": "reject", "name": "김관계", "code": "visual structure", "answers": {}}),
    "G3-6": lambda S: S["approval"]["answers"].update(Q2="아니오"),
    "G4-1": lambda S: drop_frame(S, REVIEW),
    "G4-2": lambda S: S["tokens"]["colors"].update(brand="#123456"),
    "G4-3": lambda S: S["components"].append("mystery-card"),
    "G4-4": lambda S: S["components"].remove("text-input"),
    "C-1": lambda S: node(S, MINE, "title").update(fills=[solid("#ff0000")]),
    "C-2": m_c2,
    "C-3": lambda S: node(S, MINE, "button-primary").update(fills=[solid(COLOR["accent"])]),
    "T-1": lambda S: node(S, MINE, "title")["style"].update(fontFamily="Roboto", fontPostScriptName="Roboto-Bold"),
    "T-1--font-fallback": m_t1_fallback,
    "T-2": m_t2,
    "T-3": lambda S: node(S, MINE, "title")["style"].update(letterSpacing=0.5),
    "T-4": lambda S: node(S, MINE, "title").update(characters="MY ASSETS PAGE"),
    "R-1": lambda S: node(S, MINE, "asset-card").update(cornerRadius=8),
    "R-2": lambda S: node(S, MINE, "button-primary").update(cornerRadius=16),
    "R-3": m_r3,
    "R-4": m_r4,
    "L-1": lambda S: node(S, MINE, "asset-card").update(itemSpacing=10),
    "L-2": lambda S: node(S, MINE, "asset-card")["absoluteBoundingBox"].update(x=1008),
    "L-3": lambda S: get_frame(S, MINE)["absoluteBoundingBox"].update(height=800),
    "L-4": lambda S: node(S, MINE, "button-primary")["absoluteBoundingBox"].update(height=40),
    "I-1": lambda S: S.update(post=post_i1),
    "I-2": lambda S: S.update(post=post_i2),
}


def main():
    (HERE / "banned-terms.txt").write_text("# 테스트용 금지어. 실제 목록은 rules/banned-terms.txt\n카카오뱅크\n", encoding="utf-8")
    write_fixture(HERE / "pass", build_base())
    shutil.rmtree(HERE / "fail", ignore_errors=True)
    for name, mutate in FAILS.items():
        S = build_base()
        mutate(S)
        write_fixture(HERE / "fail" / name, S)
    return len(FAILS)


if __name__ == "__main__":
    print(f"샘플 생성: 정상 1세트 + 위반 {main()}개")
