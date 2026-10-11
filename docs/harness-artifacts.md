# 하네스 산출물 (R4)

## 규칙 SSOT
- SSOT는 `docs/design.md` 1개다.
- `rules/rules.json`은 스크립트가 `docs/design.md`에서 뽑아 만드는 생성물이다. 손으로 고치지 않는다.
- `docs/design.md`가 `{그룹.이름}` 형태로 참조하는 토큰 중 값이 없는 것이 1개라도 있으면 생성이 실패한다.
- `rules/rules.json`에는 생성 당시 `docs/design.md`의 해시를 적는다. 해시가 다르면 판정 전에 다시 생성한다.

## 실행 폴더
`runs/<YYYYMMDD>-<화면슬러그>/`

- 대상 화면이 1개: 그 화면의 슬러그. 예) `runs/20261011-my-assets/`
- 대상 화면이 2개 이상: 첫 화면 슬러그 + `-plus<나머지 개수>`. 예) `runs/20261011-home-plus2/`
- 같은 이름의 폴더가 이미 있으면 `-2`, `-3`을 붙인다.

| 화면명 | 슬러그 |
|---|---|
| 홈 | `home` |
| 무료 학습자료 | `free-content` |
| 유료 멤버 자료실 | `member-library` |
| 스킬 라이브러리 | `skill-library` |
| 미션 상세 | `mission-detail` |
| 제출 화면 | `submission` |
| 내 학습 | `my-learning` |
| 내 자산 | `my-assets` |
| 자산 상세 | `asset-detail` |
| 운영자 검수 화면 | `admin-review` |

## 단계별 파일

| 단계 | 파일 | 내용 |
|---|---|---|
| 공통 | `input.json` | 대상 화면명, 유저스토리 번호 |
| 공통 | `state.json` | 현재 단계, 게이트별 결과, S5→S4 복귀 횟수, 통과한 폴더의 해시 |
| S1 | `s1-reference/references.json` | 수집본 (uibowl URL, 앱명) |
| S1 | `s1-reference/adopt.md` | 반영 항목 (YAML 블록) |
| S2 | `s2-spec/screen-spec.md` | 화면설계서 |
| S3 | `s3-keyscreen/keyscreens.json` | G3 판정에 쓴 Figma 응답 (스크립트가 씀) |
| S3 | `s3-keyscreen/approval.json` | 컨펌 기록 (승인/반려, 사유 코드) |
| S4 | `s4-build/tokens.json` | 디자인 토큰 |
| S4 | `s4-build/components.json` | 컴포넌트 목록 |
| S4 | `s4-build/screens.json` | G4 판정에 쓴 Figma 응답 (스크립트가 씀) |
| S5 | `s5-review/figma-snapshot.json` | S5 판정에 쓴 Figma 응답 (스크립트가 씀) |
| S5 | `s5-review/violations.json` | 위반 목록 |
| S5 | `s5-review/report.md` | 사람이 읽는 리포트 |

- 판정 스크립트는 G3, G4, S5를 판정할 때마다 Figma REST API에서 노드를 직접 읽는다. 저장된 스냅샷이나 에이전트가 적은 값으로 판정하지 않는다.
- `keyscreens.json`, `screens.json`, `figma-snapshot.json`은 판정에 쓴 응답을 남긴 기록이다. 스크립트만 쓰고, 에이전트는 쓰지 않는다.
- `designer`와 `builder`가 로컬에 남기는 파일은 메모(`notes.md`), `tokens.json`, `components.json`뿐이다. `tokens.json`과 `components.json`은 G4에서만 쓰고 S5 판정에는 쓰지 않는다.

## 재개
- 단계 단위로 재개한다.
- `state.json`에 마지막으로 통과한 게이트를 적고, 다시 실행하면 그 다음 단계부터 시작한다.
- 통과했다고 적힌 단계의 산출물 파일이 1개라도 없으면 그 단계부터 다시 한다.
- 복귀(R3의 되돌아가는 지점)가 일어나면 복귀 단계 이후 폴더를 비우고 `state.json`을 그 단계로 되돌린다.
