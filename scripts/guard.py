"""파일 쓰기 직전 훅. 진행 중인 실행이 있으면 현재 단계 폴더 밖 쓰기를 막는다.

.claude/settings.json의 PreToolUse(Write|Edit|NotebookEdit)에 등록한다.
stdin으로 훅 입력 JSON을 받고, 막을 때는 종료 코드 2와 stderr 메시지를 낸다.
"""
import json
import os
import sys
from pathlib import Path

from harness_lib import ROOT, SCRIPT_OWNED, STAGE_DIRS, active_runs, utf8_stdio


def _inside(path, parent):
    path = os.path.normcase(os.path.abspath(path))
    parent = os.path.normcase(os.path.abspath(parent))
    return path == parent or path.startswith(parent + os.sep)


def decide(file_path, root=ROOT):
    """(허용 여부, 이유)"""
    if not file_path or not _inside(file_path, root):
        return True, "프로젝트 밖"
    runs = active_runs(root)
    if not runs:
        return True, "진행 중인 실행 없음"
    if Path(file_path).name in SCRIPT_OWNED:
        return False, f"{Path(file_path).name}은 스크립트만 쓴다"
    open_dirs = []
    for run_dir, state in runs:
        stage_dir = STAGE_DIRS.get(state.get("stage")) if state.get("status") == "running" else None
        if stage_dir and stage_dir != STAGE_DIRS["S5"]:
            open_dirs.append(run_dir / stage_dir)
            if _inside(file_path, run_dir / stage_dir):
                return True, "현재 단계 폴더"
    allowed = ", ".join(d.relative_to(root).as_posix() + "/" for d in open_dirs) or "없음 (컨펌 대기 또는 판정 단계)"
    return False, f"실행 중에는 현재 단계 폴더에만 쓸 수 있다. 지금 쓸 수 있는 곳: {allowed}"


def main():
    utf8_stdio()
    try:
        data = json.loads(sys.stdin.buffer.read().decode("utf-8") or "{}")
        tool_input = data.get("tool_input") or {}
        file_path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
        ok, reason = decide(file_path)
    except Exception:
        return 0  # 훅 자체 오류로 세션 전체를 막지 않는다. 빠진 부분은 게이트의 해시 검사가 잡는다.
    if ok:
        return 0
    print(f"하네스 훅이 막음: {file_path}\n{reason}\n우회하지 말고 이 파일을 쓸 수 있는 에이전트나 스크립트에 맡긴다.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
