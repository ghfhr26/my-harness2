"""실행 폴더와 상태 파일 관리. input.json, state.json, approval.json은 이 스크립트만 쓴다.

사용:
  python scripts/run.py start --screens "내 자산, 자산 상세" --stories "3, 4"
  python scripts/run.py status [실행 폴더명]
  python scripts/run.py confirm approve --name <컨펌자> --q1 예 --q2 예 --q3 예 [--run 폴더명]
  python scripts/run.py confirm reject --code <visual|structure|direction> --memo "<메모>" [--run 폴더명]
  python scripts/run.py retry [실행 폴더명]     중단된 실행을 다시 연다 (실행자가 지시했을 때만)
  python scripts/run.py relock [실행 폴더명]    docs/rules/scripts를 고친 뒤 실행에 다시 묶는다 (실행자가 지시했을 때만)
  python scripts/run.py review                  실행 기록 집계
"""
import argparse
import datetime
import re
import shutil
import sys
from pathlib import Path

import gate as G
from harness_lib import (
    ROOT, SCREEN_SLUGS, STAGE_DIRS, STAGES, latest_run, load_state, lock_hash,
    now, read_json, review_lines, runs_dir, save_state, utf8_stdio, write_json,
)

TESTS_OK = ROOT / ".harness" / "tests-ok.json"
REJECT_TARGET = {"visual": "S3", "structure": "S2", "direction": "S1"}
NEXT_ACTION = {
    "G0": "judge에게 G0 판정을 맡긴다",
    "S1": "researcher 호출 → judge에게 G1",
    "S2": "spec-writer 호출 → judge에게 G2",
    "S3": "designer 호출 → judge에게 G3",
    "S4": "builder 호출 → judge에게 G4",
    "S5": "judge에게 S5 판정을 맡긴다",
    "DONE": "완료됨",
}


def tests_verified():
    ok = read_json(TESTS_OK, {}) or {}
    return ok.get("lock") == lock_hash()


def split_list(text):
    return [x.strip() for x in re.split(r"[,/]", text or "") if x.strip()]


def resolve_run(name):
    if name:
        path = runs_dir() / name
        if not (path / "state.json").exists():
            sys.exit(f"실행 폴더가 없다: runs/{name}")
        return path
    path = latest_run()
    if not path:
        sys.exit("실행이 하나도 없다")
    return path


def cmd_start(args):
    if not tests_verified():
        print("시작 불가: 판정 스크립트 검증이 현재 docs/rules/scripts 기준으로 통과하지 않았다.")
        print("  python scripts/test_gates.py 를 먼저 통과시킨다.")
        return 1
    stories = []
    for s in split_list(args.stories):
        stories.append(int(s) if s.isdigit() else s)
    inp = {"screens": split_list(args.screens), "stories": stories}
    violations = G.check_input(inp)
    if violations:
        print("G0 미통과: 실행을 시작하지 않는다.")
        G.print_violations("G0", violations)
        return 1
    screens = inp["screens"]
    slug = SCREEN_SLUGS[screens[0]] + (f"-plus{len(screens) - 1}" if len(screens) > 1 else "")
    base = f"{datetime.date.today():%Y%m%d}-{slug}"
    name, n = base, 2
    while (runs_dir() / name).exists():
        name, n = f"{base}-{n}", n + 1
    run = runs_dir() / name
    for d in STAGE_DIRS.values():
        (run / d).mkdir(parents=True)
    write_json(run / "input.json", {**inp, "created": now()})
    save_state(run, {
        "run": name, "created": now(), "stage": "G0", "status": "running",
        "gates": {}, "retries": {}, "s5_returns": 0, "hashes": {},
        "violation_counts": {}, "confirm_history": [], "lock": lock_hash(),
    })
    print(f"실행 폴더: runs/{name}")
    print("다음:", NEXT_ACTION["G0"])
    return 0


def cmd_status(args):
    run = resolve_run(args.run)
    st = load_state(run)
    inp = read_json(run / "input.json", {}) or {}
    print(f"실행: runs/{run.name}")
    print(f"대상 화면: {', '.join(inp.get('screens') or [])} / 스토리 {inp.get('stories')}")
    print(f"단계: {st.get('stage')} · 상태: {st.get('status')}" + (f" ({st['halt_reason']})" if st.get("status") == "halted" and st.get("halt_reason") else ""))
    for g in G.GATES:
        r = (st.get("gates") or {}).get(g)
        if r:
            print(f"  {g}: {r['result']} (위반 {r['violations']}건, {r['at']}) · 미통과 {st.get('retries', {}).get(g, 0)}회")
    print(f"S5→S4 복귀: {st.get('s5_returns', 0)}회 · 컨펌 반려: {len(st.get('confirm_history') or [])}회")
    if st.get("status") == "waiting_confirm":
        print("다음: 사람 컨펌을 기다린다 (컨펌 승인 <이름> / 컨펌 반려 <코드> <메모>)")
    elif st.get("status") == "halted":
        print("다음: 실행자 판단을 기다린다")
    else:
        print("다음:", NEXT_ACTION.get(st.get("stage"), ""))
    return 0


def cmd_confirm(args):
    run = resolve_run(args.run)
    st = load_state(run)
    if st.get("status") != "waiting_confirm":
        print(f"기록하지 않음: 지금은 컨펌 대기가 아니다 (단계 {st.get('stage')} · 상태 {st.get('status')})")
        return 1
    answers = {"Q1": args.q1, "Q2": args.q2, "Q3": args.q3}
    violations = G.check_confirm(args.action, args.name, args.code, answers)
    if violations:
        print("기록하지 않음:")
        G.print_violations("G3", violations)
        if args.action == "approve" and any(x["rule"] == "G3-6" for x in violations):
            print("  문항에 아니오가 있으면 승인할 수 없다. 반려 사유 코드를 묻는다.")
        return 1
    s3 = run / STAGE_DIRS["S3"]
    if args.action == "approve":
        write_json(s3 / "approval.json", {
            "result": "승인", "code": None, "name": args.name.strip(), "date": now(),
            "answers": answers, "memo": args.memo or "",
        })
        st["status"] = "running"
        save_state(run, st)
        print("승인 기록 완료. 다음: judge에게 G3 판정을 다시 맡긴다")
        return 0
    code = args.code.strip()
    target = REJECT_TARGET[code]
    st.setdefault("confirm_history", []).append({
        "result": "반려", "code": code, "name": (args.name or "").strip(), "date": now(), "memo": args.memo or "",
    })
    # 복귀 단계 이후의 산출물은 전부 다시 만든다. 복귀 단계 자체는 고쳐 쓴다.
    idx = STAGES.index(target)
    for stage in STAGES[idx + 1:]:
        d = run / STAGE_DIRS[stage]
        shutil.rmtree(d, ignore_errors=True)
        d.mkdir(parents=True, exist_ok=True)
    for name in ("approval.json", "keyscreens.json"):
        (s3 / name).unlink(missing_ok=True)
    for stage in STAGES[idx:]:
        (st.get("hashes") or {}).pop(stage, None)
    for g, stage in G.GATE_STAGE.items():
        if stage in STAGES[idx:]:
            st.get("gates", {}).pop(g, None)
            st.get("retries", {}).pop(g, None)
    st["s5_returns"] = 0
    st["stage"] = target
    st["status"] = "running"
    save_state(run, st)
    print(f"반려 기록 완료 (사유 {code}). 단계 {target}로 복귀. 다음: {NEXT_ACTION[target]}")
    return 0


def cmd_retry(args):
    run = resolve_run(args.run)
    st = load_state(run)
    if st.get("status") != "halted":
        print(f"중단된 실행이 아니다 (상태 {st.get('status')})")
        return 1
    gate = next((g for g, s in G.GATE_STAGE.items() if s == st.get("stage")), None)
    if gate:
        st.get("retries", {}).pop(gate, None)
    if st.get("stage") == "S5":
        st["stage"] = "S4"
        st["s5_returns"] = 0
        (st.get("hashes") or {}).pop("S4", None)
    st["status"] = "running"
    st.pop("halt_reason", None)
    save_state(run, st)
    print(f"실행을 다시 열었다. 단계 {st['stage']}. 다음: {NEXT_ACTION.get(st['stage'], '')}")
    return 0


def cmd_relock(args):
    run = resolve_run(args.run)
    if not tests_verified():
        print("묶지 않음: 고친 docs/rules/scripts 기준으로 python scripts/test_gates.py 가 통과해야 한다.")
        return 1
    st = load_state(run)
    st["lock"] = lock_hash()
    save_state(run, st)
    print("현재 docs/rules/scripts 기준으로 실행을 다시 묶었다.")
    return 0


def cmd_review(args):
    lines = review_lines(force=True)
    print("\n".join(lines) if lines else "실행 기록이 없다")
    return 0


def main():
    utf8_stdio()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("start")
    s.add_argument("--screens", required=True)
    s.add_argument("--stories", required=True)
    s.set_defaults(fn=cmd_start)
    for name, fn in (("status", cmd_status), ("retry", cmd_retry), ("relock", cmd_relock)):
        s = sub.add_parser(name)
        s.add_argument("run", nargs="?")
        s.set_defaults(fn=fn)
    s = sub.add_parser("confirm")
    s.add_argument("action", choices=["approve", "reject"])
    s.add_argument("--run")
    s.add_argument("--name", default="")
    s.add_argument("--code", default="")
    s.add_argument("--memo", default="")
    for q in ("q1", "q2", "q3"):
        s.add_argument(f"--{q}", default="")
    s.set_defaults(fn=cmd_confirm)
    s = sub.add_parser("review")
    s.set_defaults(fn=cmd_review)
    args = p.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
