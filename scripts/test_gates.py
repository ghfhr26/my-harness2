"""판정 스크립트 검증. 하네스를 쓰기 전에, 그리고 조건이나 스크립트를 고칠 때마다 돌린다.

확인하는 것:
  1. scripts/gate.py의 규칙 ID와 docs/harness-gates.md의 규칙 ID가 같다
  2. 정상 세트(tests/pass)에서 위반 0건
  3. 위반 샘플(tests/fail/<규칙 ID>)마다 그 규칙으로 정확히 1건, 다른 규칙으로 0건
  4. 샘플이 없는 규칙 0건
  5. 훅(guard.py)이 허용 경로는 통과시키고 차단 경로는 막는다
전부 통과하면 .harness/tests-ok.json에 기록한다. 이 기록이 없으면 `디자인 시작`을 받지 않는다.

사용: python scripts/test_gates.py
"""
import re
import shutil
import sys
from pathlib import Path

import gate as G
import guard
from harness_lib import ROOT, lock_hash, now, read_json, read_text, utf8_stdio, write_json

TESTS = ROOT / "tests"
sys.path.insert(0, str(TESTS))


def doc_rule_ids():
    text = read_text(ROOT / "docs" / "harness-gates.md")
    return set(re.findall(r"(?m)^\|\s*★?([A-Z][0-9]?-[0-9]+)\s*\|", text))


def check_guard():
    root = TESTS / "guard-root"
    shutil.rmtree(root, ignore_errors=True)
    run = root / "runs" / "r1"
    (run / "s1-reference").mkdir(parents=True)
    write_json(run / "state.json", {"run": "r1", "stage": "S1", "status": "running"})
    cases = [
        (run / "s1-reference" / "adopt.md", True, "현재 단계 폴더"),
        (root / "docs" / "design.md", False, "docs/"),
        (run / "s2-spec" / "screen-spec.md", False, "다른 단계 폴더"),
        (run / "s3-keyscreen" / "approval.json", False, "approval.json"),
        (run / "state.json", False, "state.json"),
        (root.parent.parent.parent / "elsewhere.txt", True, "프로젝트 밖"),
    ]
    problems = []
    for path, want, what in cases:
        got, _ = guard.decide(str(path), root)
        if got != want:
            problems.append(f"guard: {what} → {'허용' if got else '차단'} (기대: {'허용' if want else '차단'})")
    write_json(run / "state.json", {"run": "r1", "stage": "S1", "status": "done"})
    if not guard.decide(str(root / "docs" / "design.md"), root)[0]:
        problems.append("guard: 진행 중인 실행이 없는데 막음")
    shutil.rmtree(root, ignore_errors=True)
    return problems, len(cases) + 1


def main():
    utf8_stdio()
    import make_fixtures
    n_fail = make_fixtures.main()
    problems = []

    code_ids, doc_ids = set(G.RULES), doc_rule_ids()
    for rid in sorted(code_ids - doc_ids):
        problems.append(f"규칙 {rid}: gate.py에는 있고 docs/harness-gates.md에는 없다")
    for rid in sorted(doc_ids - code_ids):
        problems.append(f"규칙 {rid}: docs/harness-gates.md에는 있고 gate.py에는 없다")

    got = G.run_all(TESTS / "pass")
    for x in got:
        problems.append(f"정상 세트에서 위반: [{x['rule']}] {x['detail']} {x['actual']}")

    covered = set()
    for d in sorted((TESTS / "fail").iterdir()):
        rid = d.name.split("--")[0]
        covered.add(rid)
        if (d / "confirm.json").exists():
            args = read_json(d / "confirm.json")
            got = G.check_confirm(args["action"], args.get("name"), args.get("code"), args.get("answers"))
        else:
            got = G.run_all(d)
        hits = [x for x in got if x["rule"] == rid]
        others = sorted({x["rule"] for x in got if x["rule"] != rid})
        if len(hits) != 1:
            problems.append(f"샘플 {d.name}: {rid}로 {len(hits)}건 (기대 1건)")
        if others:
            problems.append(f"샘플 {d.name}: 다른 규칙에도 걸림 → {', '.join(others)}")
    for rid in sorted(code_ids - covered):
        problems.append(f"규칙 {rid}: 위반 샘플이 없다")

    guard_problems, n_guard = check_guard()
    problems += guard_problems

    ok_file = ROOT / ".harness" / "tests-ok.json"
    print(f"규칙 {len(code_ids)}개 · 정상 세트 1개 · 위반 샘플 {n_fail}개 · 훅 검사 {n_guard}건")
    if problems:
        ok_file.unlink(missing_ok=True)
        print(f"실패 {len(problems)}건")
        for p in problems:
            print(" -", p)
        return 1
    write_json(ok_file, {"lock": lock_hash(), "at": now(), "rules": len(code_ids), "fail_fixtures": n_fail})
    print("전부 통과")
    return 0


if __name__ == "__main__":
    sys.exit(main())
