"""docs/design.md → rules/rules.json 생성.

rules.json은 생성물이다. 손으로 고치지 않는다.
design.md가 참조하는 토큰 중 값이 없는 것이 있으면 실패한다.
사용: python scripts/build_rules.py
"""
import re
import sys

from harness_lib import ROOT, read_text, sha_file, utf8_stdio, write_json

DESIGN = ROOT / "docs" / "design.md"
OUT = ROOT / "rules" / "rules.json"


def build(design_path=DESIGN):
    text = read_text(design_path)
    colors = {
        m.group(1): m.group(2).lower()
        for m in re.finditer(r"\(`\{colors\.([a-z0-9-]+)\}` — (#[0-9a-fA-F]{6})\)", text)
    }
    typography = {}
    for m in re.finditer(
        r"(?m)^\|\s*`\{typography\.([a-z0-9-]+)\}`\s*\|\s*(\d+)px\s*\|\s*(\d+)\s*\|\s*([\d.]+)\s*\|\s*([\d.-]+)\s*\|",
        text,
    ):
        typography[m.group(1)] = {
            "size": int(m.group(2)),
            "weight": int(m.group(3)),
            "lineHeight": float(m.group(4)),
            "letterSpacing": float(m.group(5)),
        }
    spacing = {m.group(1): int(m.group(2)) for m in re.finditer(r"`\{spacing\.([a-z0-9-]+)\}` (\d+)px", text)}
    rounded = {
        m.group(1): int(m.group(2))
        for m in re.finditer(r"(?m)^\|\s*`\{rounded\.([a-z0-9-]+)\}`\s*\|\s*(\d+)px\s*\|", text)
    }
    components = sorted(set(re.findall(r"\*\*`([a-z0-9-]+)`\*\*", text)))
    # 토큰이 아닌 색: badge-overlay의 rgba
    extra_colors = sorted({
        "#%02x%02x%02x" % (int(m.group(1)), int(m.group(2)), int(m.group(3)))
        for m in re.finditer(r"rgba\((\d+),\s*(\d+),\s*(\d+),\s*[\d.]+\)", text)
    })
    families = sorted(set(re.findall(r"(?m)^\*\*([A-Za-z ]+)\*\* — a .*used exclusively", text)))

    groups = {"colors": colors, "typography": typography, "spacing": spacing, "rounded": rounded}
    missing = sorted({
        f"{g}.{n}"
        for g, n in re.findall(r"\{(colors|typography|spacing|rounded)\.([a-z0-9-]+)\}", text)
        if n not in groups[g]
    })
    rules = {
        "design_sha256": sha_file(design_path),
        "font_family": families[0] if families else "",
        "colors": colors,
        "extra_colors": extra_colors,
        "typography": typography,
        "spacing": spacing,
        "rounded": rounded,
        "components": components,
    }
    return rules, missing


def main():
    utf8_stdio()
    rules, missing = build()
    problems = [f"값이 없는 토큰: {m}" for m in missing]
    for key in ("colors", "typography", "spacing", "rounded", "components"):
        if not rules[key]:
            problems.append(f"{key}를 하나도 찾지 못했다")
    if not rules["font_family"]:
        problems.append("서체 패밀리를 찾지 못했다")
    if problems:
        print("rules.json 생성 실패")
        for p in problems:
            print(" -", p)
        return 1
    write_json(OUT, rules)
    print(f"rules/rules.json 생성: 색 {len(rules['colors'])} · 서체 {len(rules['typography'])} · "
          f"간격 {len(rules['spacing'])} · 모서리 {len(rules['rounded'])} · 컴포넌트 {len(rules['components'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
