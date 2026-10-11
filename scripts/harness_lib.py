"""하네스 공용 함수: 경로, 해시, 상태 파일, 문서 파싱, Figma 읽기."""
import datetime
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

STAGES = ["S1", "S2", "S3", "S4", "S5"]
STAGE_DIRS = {
    "S1": "s1-reference",
    "S2": "s2-spec",
    "S3": "s3-keyscreen",
    "S4": "s4-build",
    "S5": "s5-review",
}
# 스크립트만 쓰는 파일. 에이전트는 쓰지 않는다.
SCRIPT_OWNED = {
    "input.json", "state.json", "approval.json", "keyscreens.json",
    "screens.json", "figma-snapshot.json", "violations.json", "report.md",
}
SCREEN_SLUGS = {
    "홈": "home",
    "무료 학습자료": "free-content",
    "유료 멤버 자료실": "member-library",
    "스킬 라이브러리": "skill-library",
    "미션 상세": "mission-detail",
    "제출 화면": "submission",
    "내 학습": "my-learning",
    "내 자산": "my-assets",
    "자산 상세": "asset-detail",
    "운영자 검수 화면": "admin-review",
}
LOCK_DIRS = ["docs", "rules", "scripts"]
ACTIVE_STATUSES = {"running", "waiting_confirm"}


def utf8_stdio():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


def now():
    return datetime.datetime.now().isoformat(timespec="seconds")


def read_text(path):
    return Path(path).read_text(encoding="utf-8")


def read_json(path, default=None):
    path = Path(path)
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return default


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sha_dir(path):
    """폴더 안 파일별 해시. {상대경로: sha256}"""
    path = Path(path)
    out = {}
    if not path.exists():
        return out
    for f in sorted(path.rglob("*")):
        if f.is_file() and "__pycache__" not in f.parts and f.suffix != ".pyc":
            out[f.relative_to(path).as_posix()] = sha_file(f)
    return out


def lock_hash(root=ROOT, dirs=LOCK_DIRS):
    """docs/, rules/, scripts/ 전체를 하나의 해시로 묶는다."""
    h = hashlib.sha256()
    for d in dirs:
        for rel, sha in sha_dir(Path(root) / d).items():
            h.update(f"{d}/{rel}:{sha}\n".encode("utf-8"))
    return h.hexdigest()


def load_state(run_dir):
    return read_json(Path(run_dir) / "state.json", {}) or {}


def save_state(run_dir, state):
    write_json(Path(run_dir) / "state.json", state)


def runs_dir(root=ROOT):
    return Path(root) / "runs"


def all_runs(root=ROOT):
    base = runs_dir(root)
    out = []
    if base.exists():
        for d in base.iterdir():
            if d.is_dir() and (d / "state.json").exists():
                out.append((d, load_state(d)))
    return out


def active_runs(root=ROOT):
    return [(d, s) for d, s in all_runs(root) if s.get("status") in ACTIVE_STATUSES]


def latest_run(root=ROOT):
    runs = sorted(all_runs(root), key=lambda x: x[1].get("created", ""))
    return runs[-1][0] if runs else None


# ---------- 문서 파싱 ----------

YAML_BLOCK = re.compile(r"```ya?ml\s*\n(.*?)```", re.S)


def yaml_blocks(text):
    out = []
    for m in YAML_BLOCK.finditer(text or ""):
        try:
            out.append(yaml.safe_load(m.group(1)))
        except yaml.YAMLError:
            out.append(None)
    return out


def spec_sections(text):
    """screen-spec.md → [(화면명, YAML 블록 dict)]. 블록이 없거나 깨졌으면 {}."""
    out = []
    parts = re.split(r"(?m)^##\s+(.+?)\s*$", text or "")
    for i in range(1, len(parts), 2):
        blocks = [b for b in yaml_blocks(parts[i + 1]) if isinstance(b, dict)]
        out.append((parts[i].strip(), blocks[0] if blocks else {}))
    return out


def adopt_items(text):
    """adopt.md → 반영 항목 리스트."""
    items = []
    for b in yaml_blocks(text):
        if isinstance(b, dict):
            b = b.get("items")
        if isinstance(b, list):
            items.extend(x for x in b if isinstance(x, dict))
    return items


# ---------- Figma ----------

class FigmaError(Exception):
    pass


def figma_file_key(url):
    m = re.search(r"figma\.com/(?:design|file)/([A-Za-z0-9]+)", url or "")
    return m.group(1) if m else None


def _figma_get(path):
    token = os.environ.get("FIGMA_TOKEN", "").strip()
    if not token:
        raise FigmaError("환경 변수 FIGMA_TOKEN이 없다")
    req = urllib.request.Request("https://api.figma.com" + path, headers={"X-Figma-Token": token})
    try:
        with urllib.request.urlopen(req, timeout=120) as res:
            return json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise FigmaError(f"Figma API 응답 {e.code}") from e
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        raise FigmaError(f"Figma API 접속 실패: {e}") from e


def fetch_figma_page(file_url, page_name, fixture_dir=None):
    """Figma 파일에서 page_name 페이지를 통째로 읽는다.

    값은 Figma REST API 응답 그대로다. 에이전트가 적은 값은 한 줄도 섞이지 않는다.
    fixture_dir가 있으면(테스트) 같은 모양의 저장된 응답을 읽는다.
    """
    if fixture_dir:
        fdir = Path(fixture_dir) / "figma"
        file_doc = read_json(fdir / "file.json")
        if file_doc is None:
            raise FigmaError("Figma 파일을 읽을 수 없다")
        key = "fixture"
    else:
        key = figma_file_key(file_url)
        if not key:
            raise FigmaError("figma_file_url에서 파일 키를 찾을 수 없다")
        file_doc = _figma_get(f"/v1/files/{key}?depth=1")
    pages = (file_doc.get("document") or {}).get("children") or []
    page = next((p for p in pages if p.get("name") == page_name), None)
    result = {
        "source": "fixture" if fixture_dir else "figma-rest-api",
        "file_key": key,
        "page": page_name,
        "page_id": page.get("id") if page else None,
        "fetched_at": now(),
        "components": {},
        "componentSets": {},
        "frames": [],
    }
    if not page:
        return result
    if fixture_dir:
        nodes_doc = read_json(Path(fixture_dir) / "figma" / "nodes.json") or {}
    else:
        nodes_doc = _figma_get(f"/v1/files/{key}/nodes?ids={page['id']}")
    entry = (nodes_doc.get("nodes") or {}).get(page["id"]) or {}
    result["components"] = entry.get("components") or {}
    result["componentSets"] = entry.get("componentSets") or {}
    result["frames"] = [
        n for n in (entry.get("document") or {}).get("children") or []
        if n.get("type") == "FRAME" and n.get("visible", True) is not False
    ]
    return result


def figma_page_link(file_url, page_id):
    key = figma_file_key(file_url)
    if not key or not page_id:
        return file_url or ""
    return f"https://www.figma.com/design/{key}/?node-id={page_id.replace(':', '-')}"


# ---------- 실행 기록 ----------

SUMMARY_COLUMNS = ["date", "run", "screens", "result", "retries", "s5_returns", "violations", "reject_codes"]


def _pairs(d):
    return ";".join(f"{k}={v}" for k, v in sorted((d or {}).items()))


def append_summary(run_dir, state, result, root=ROOT):
    """실행이 끝나거나 중단될 때 runs/summary.csv에 1줄을 추가한다."""
    import csv
    path = runs_dir(root) / "summary.csv"
    new = not path.exists()
    inp = read_json(Path(run_dir) / "input.json", {}) or {}
    with path.open("a", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(SUMMARY_COLUMNS)
        w.writerow([
            now()[:10], Path(run_dir).name, ";".join(inp.get("screens") or []), result,
            _pairs(state.get("retries")), state.get("s5_returns", 0),
            _pairs(state.get("violation_counts")),
            ";".join(h.get("code", "") for h in state.get("confirm_history") or []),
        ])


def review_lines(root=ROOT, force=False):
    """완료된 실행이 5개 쌓일 때마다 보여줄 집계. 해당 없으면 빈 리스트."""
    import csv
    path = runs_dir(root) / "summary.csv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    done = [r for r in rows if r.get("result") == "완료"]
    if not force and (not done or len(done) % 5 != 0):
        return []
    rules, gates = {}, {}
    for r in rows:
        for target, col in ((rules, "violations"), (gates, "retries")):
            for pair in filter(None, (r.get(col) or "").split(";")):
                k, _, n = pair.partition("=")
                target[k] = target.get(k, 0) + int(n or 0)
    top = sorted(rules.items(), key=lambda x: -x[1])[:3]
    worst = max(gates.items(), key=lambda x: x[1]) if gates else None
    lines = [f"하네스 리뷰: 실행 {len(rows)}회 (완료 {len(done)}회)"]
    lines.append("  위반 상위 규칙: " + (", ".join(f"{k} {n}건" for k, n in top) or "없음"))
    lines.append("  재시도가 가장 많은 게이트: " + (f"{worst[0]} {worst[1]}회" if worst else "없음"))
    return lines
