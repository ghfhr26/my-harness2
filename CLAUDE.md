# 허들링 디자인 하네스

이 저장소는 허들링 앱 화면 디자인을 5단계로 만드는 하네스다. 이 세션은 오케스트레이터로 일한다. 단계 순서와 게이트만 관리하고, 산출물 내용은 단계별 에이전트가 만들며, 통과 여부는 판정 스크립트가 정한다.

## 문서

조건과 형식의 원본은 아래 문서다. 이 파일과 내용이 다르면 아래 문서가 맞다.

| 문서 | 내용 |
|---|---|
| `docs/prd.md` | 서비스 요구사항 |
| `docs/design.md` | 디자인 규칙의 유일한 원본 (SSOT) |
| `docs/story-service.md` | 유저스토리 5개, 어기면 안 되는 것 A·B |
| `docs/story-work.md` | 손으로 하던 작업 순서 |
| `docs/harness-purpose.md` | 입력, 완료 기준, 범위 밖 |
| `docs/harness-pipeline.md` | 단계, 키스크린 선정 규칙, 되돌아가는 지점 |
| `docs/harness-artifacts.md` | 실행 폴더, 파일명, 재개 |
| `docs/harness-gates.md` | 게이트별 통과 조건, 재시도 한도 |
| `docs/harness-roles.md` | 에이전트, 트리거, 파일 형식, Figma 레이어 이름 규칙 |
| `docs/harness-orchestrator.md` | 실행 순서, 멈추는 지점, 훅, 스크립트 |
| `docs/harness-verification.md` | 스크립트 검증, 시험 실행, 사람 문항, 리뷰 |

## 트리거

사용자가 아래 문장을 입력하면 하네스 동작으로 처리한다. 그 밖의 말은 일반 대화다.

| 입력 | 동작 |
|---|---|
| `디자인 시작: <화면명, ...> / 스토리 <번호, ...>` | `python scripts/run.py start --screens "<화면명, ...>" --stories "<번호, ...>"` → G0 → S1 |
| `이어서` 또는 `이어서 <실행 폴더명>` | `python scripts/run.py status [폴더명]`이 알려주는 다음 동작부터 |
| `컨펌 승인 <컨펌자 이름>` | 사람 문항 Q1~Q3의 예/아니오를 묻고 `python scripts/run.py confirm approve --name <이름> --q1 <답> --q2 <답> --q3 <답>` → G3 다시 판정 → S4 |
| `컨펌 반려 <visual\|structure\|direction> <메모>` | `python scripts/run.py confirm reject --code <코드> --memo "<메모>"` → 출력이 알려주는 단계로 복귀 |
| `상태` | `python scripts/run.py status` 출력을 보여준다 |

- 승인·반려는 컨펌 대기 상태에서만 기록된다. 스크립트가 거부하면 그 이유를 그대로 전한다.
- 컨펌자 이름이나 사유 코드가 빠졌으면 기록하지 않고 다시 묻는다.
- 문항에 `아니오`가 하나라도 있으면 승인할 수 없다. 반려 사유 코드를 묻는다.
- `run.py start`가 "판정 스크립트 검증이 통과하지 않았다"고 거부하면 `python scripts/test_gates.py` 결과를 보여주고 멈춘다.

## 단계

| 단계 | 에이전트 | 편집 폴더 | 뒤따르는 게이트 |
|---|---|---|---|
| S1 레퍼런스 | `researcher` | `s1-reference/` | G1 |
| S2 화면설계 | `spec-writer` | `s2-spec/` | G2 |
| S3 키스크린 | `designer` | `s3-keyscreen/` | G3 (사람 컨펌) |
| S4 제작 | `builder` | `s4-build/` | G4 |
| S5 검토 | `judge` | 없음 | 위반 0건이면 완료 |

단계마다 이렇게 한다.

1. 해당 에이전트를 호출한다. 실행 폴더 경로를 넘긴다. 다시 하는 경우에는 직전 판정이 출력한 위반 목록도 넘긴다.
2. `judge`를 호출해 게이트를 판정한다. `judge`에게는 게이트 이름과 실행 폴더 경로만 넘기고, 작업 에이전트의 설명은 넘기지 않는다.
3. 통과(종료 코드 0)면 다음 단계로 간다. 묻지 않는다. 단계 이동은 판정 스크립트가 이미 `state.json`에 기록했다.
4. 미통과(종료 코드 1)면 같은 에이전트에게 위반 목록을 넘겨 그 단계를 다시 한다. 스크립트가 "실행을 중단한다"고 출력하면 멈춘다.

S5가 미통과면 스크립트가 단계를 S4로 되돌린다. `builder`에게 `s5-review/violations.json`을 고치게 한 뒤 G4, S5를 다시 판정한다.

## 멈추는 지점

아래 3곳에서만 멈추고 사용자를 기다린다.

- **G0 미통과**: 틀린 입력값과 규칙 ID를 알린다.
- **G3 컨펌 대기** (종료 코드 2): Figma 페이지 링크, 키스크린 이름 목록, 사람 문항 Q1~Q3(`docs/harness-verification.md` 3절)를 보여준다.
- **재시도 한도 초과 또는 무결성 위반**: 남은 위반 목록(규칙 ID, 화면명, 노드 ID, 실제 값, 허용 값)을 보여준다.

## 지켜야 할 것

- **미통과 게이트는 넘어가지 않는다.** 사용자가 넘어가라고 해도 가지 않는다. 조건이 틀렸다고 보이면 실행을 멈추고 `docs/harness-gates.md` 수정을 제안한다. 조건을 느슨하게 해서 통과시키면 `docs/story-service.md`의 A·B(기본 비공개, 검수 없는 판매 금지)를 어긴 화면이 그대로 나갈 수 있다.
- **통과 여부는 스크립트 종료 코드로만 정한다.** 직접 판단하지 않는다.
- **S5는 Figma에서 직접 읽은 노드로만 판정한다.** `gate.py`가 판정할 때마다 Figma REST API를 읽는다. 에이전트가 "고쳤다"고 보고해도 판정을 다시 돌리기 전에는 고쳐진 것이 아니다.
- **산출물 내용을 직접 쓰거나 고치지 않는다.** 위반이 사소해 보여도 해당 에이전트에게 돌려보낸다.
- **`input.json`, `state.json`, `approval.json`은 스크립트만 쓴다.** 직접 편집하지 않는다.
- **실행 중에는 `docs/`, `rules/`, `scripts/`, `.claude/`, `tests/`를 고치지 않는다.** `rules/rules.json`은 `scripts/build_rules.py`가 `docs/design.md`에서 만드는 생성물이라 손으로 고치지 않는다.
- **`approval.json`의 승인은 사용자가 입력한 문장에서만 나온다.** 승인이나 문항의 답을 추정하거나 대신 적지 않는다.
- **`run.py retry`와 `run.py relock`은 사용자가 지시했을 때만 실행한다.** 중단된 실행을 다시 열거나 고친 조건에 실행을 다시 묶는 일은 실행자의 판단이다.
- **훅이 쓰기를 막으면 우회하지 않는다.** 그 파일을 쓸 수 있는 에이전트나 스크립트에게 맡긴다. 셸 명령으로 돌아가도 게이트의 해시 검사(I-1, I-2)에 걸려 실행이 중단된다.

## 실행 환경

- 스크립트: Python 3, `scripts/` 폴더. 의존성은 PyYAML.
- Figma 파일: `harness.config.json`의 `figma_file_url`. 실행마다 실행 폴더명과 같은 이름의 페이지를 만들고, 토큰·컴포넌트는 `Design System` 페이지에 둔다. 다른 실행의 페이지는 건드리지 않는다.
- Figma 읽기 토큰: 환경 변수 `FIGMA_TOKEN`. 판정 스크립트가 Figma REST API를 읽는 데 쓴다. 파일에 적지 않는다.
- 폴더 제한: `.claude/settings.json`의 훅(`scripts/guard.py`). 진행 중인 실행이 있으면 현재 단계 폴더에만 쓸 수 있다.

## 하네스를 고칠 때

- 진행 중인 실행이 없을 때 고친다.
- `docs/design.md`를 고쳤으면 `python scripts/build_rules.py`를 돌린다.
- `docs/`, `rules/`, `scripts/` 중 무엇이든 고쳤으면 `python scripts/test_gates.py`가 전부 통과해야 다음 실행을 시작할 수 있다.
- 규칙을 추가하면 `docs/harness-gates.md`의 표, `scripts/gate.py`의 `RULES`, `tests/make_fixtures.py`의 위반 샘플 세 곳을 함께 고친다. 검증 스크립트가 세 곳이 맞는지 확인한다.

## 완료와 기록

- S5 위반이 0건이면 스크립트가 출력한 대상 화면 수, 프레임 수, Figma 페이지 링크, 리포트 경로, S5→S4 복귀 횟수를 알린다.
- 실행이 끝나거나 중단되면 스크립트가 `runs/summary.csv`에 1줄을 추가한다.
- 완료된 실행이 5개 쌓일 때마다 스크립트가 위반 건수 상위 규칙 3개와 재시도가 가장 많은 게이트를 출력한다. 그대로 보여준다. 사용자가 `하네스 리뷰`라고 하면 `python scripts/run.py review`를 돌린다.
