# 하네스 역할 (R6)

## 에이전트

| 에이전트 | 단계 | 편집 폴더 (1개) | 읽기 | 외부 도구 |
|---|---|---|---|---|
| `researcher` | S1 | `runs/<실행>/s1-reference/` | `input.json`, `docs/story-service.md`, `docs/prd.md` | uibowl |
| `spec-writer` | S2 | `runs/<실행>/s2-spec/` | 위 + `s1-reference/`, `docs/design.md` | 없음 |
| `designer` | S3 | `runs/<실행>/s3-keyscreen/` | 위 + `s2-spec/`, `rules/rules.json` | figma |
| `builder` | S4 | `runs/<실행>/s4-build/` | 위 + `s3-keyscreen/`, `s5-review/violations.json` | figma |
| `judge` | G0~G4, S5 | 없음 (읽기전용) | 전부 | 없음 |

- 작업 에이전트는 자기 편집 폴더 밖의 파일을 만들거나 고치지 않는다.
- 작업 에이전트는 `docs/`, `rules/`, `scripts/`, 다른 단계 폴더를 고치지 않는다.
- `designer`는 `approval.json`을 쓰지 않는다. 같은 폴더에 있지만 `scripts/run.py`만 쓴다.

## 판정자 (읽기전용)
- `judge`는 파일 편집 도구가 없다. 판정 스크립트를 실행하고 결과를 그대로 전달한다.
- `s5-review/` 안의 파일, Figma 응답 기록, 게이트 결과는 스크립트가 쓴다.
- `judge`는 위반을 고치지 않고, 통과 여부를 스스로 판단하지 않는다. 스크립트 종료 코드가 0이면 통과, 아니면 미통과.
- `judge`는 작업 에이전트의 설명을 받지 않는다. 파일 경로만 받는다.

## 오케스트레이터 (CLAUDE.md)
- `input.json`, `state.json`, `s3-keyscreen/approval.json`은 `scripts/run.py`로만 쓴다. 직접 편집하지 않는다.
- 하는 일: 트리거 해석, 실행 폴더 생성, 단계 순서대로 에이전트 호출, 게이트마다 `judge` 호출, 복귀·재개 처리
- 산출물 내용을 직접 쓰거나 고치지 않는다.

## 자연어 트리거

| 동작 | 입력 문장 | 하는 일 |
|---|---|---|
| 시작 | `디자인 시작: <화면명, ...> / 스토리 <번호, ...>` | 실행 폴더 생성 → G0 → S1 |
| 재개 | `이어서` 또는 `이어서 <실행 폴더명>` | `state.json`의 다음 단계부터. 폴더명이 없으면 가장 최근 실행 |
| 승인 | `컨펌 승인 <컨펌자 이름>` | `approval.json` 기록 → S4 |
| 반려 | `컨펌 반려 <visual\|structure\|direction> <메모>` | `approval.json` 기록 → 사유 코드에 따라 복귀 |
| 상태 | `상태` | 현재 단계와 게이트별 결과 출력 |

- 승인·반려는 `state.json`이 G3 대기일 때만 받는다. 다른 단계에서 입력하면 기록하지 않고 현재 상태를 알린다.
- 컨펌자 이름이 없으면 기록하지 않고 다시 묻는다.

## Figma
- 고정 파일 1개를 쓴다. URL은 `harness.config.json`의 `figma_file_url`에 적는다.
- 실행마다 실행 폴더명과 같은 이름의 페이지를 만든다. 키스크린과 완성 시안은 그 페이지 안에 둔다.
- 토큰·컴포넌트는 `Design System` 페이지에 두고 실행 간에 재사용한다.
- 다른 실행의 페이지는 건드리지 않는다.

## 파일 형식

### `s1-reference/adopt.md` 반영 항목
YAML 블록 1개에 `items` 목록으로 적는다. 항목마다 ID(`A-01`부터), 레퍼런스 URL, 유저스토리 번호, 대상 화면명, 반영 내용 1문장.

```yaml
items:
  - id: A-01
    ref: https://uibowl.io/...
    story: 4
    screen: 내 자산
    text: 카드마다 상태 배지를 오른쪽 위에 둔다
```

### `s1-reference/references.json`
`{"references": [{"id": "R-01", "screen": "내 자산", "app": "앱 이름", "url": "https://uibowl.io/..."}]}`

### `s2-spec/screen-spec.md`
화면마다 `## <화면명>` 섹션 1개, 그 안에 YAML 블록 1개. 스크립트는 YAML 블록만 센다.

```yaml
screen: 내 자산
stories: [3, 4]
adopt: [A-01, A-03]
keyscreen: true
components:
  - name: button-primary
  - name: "new: asset-card"
    visibility_label: true
fields:
  - name: 공개 범위
    options: [비공개, 멤버 공개, 판매 신청]
    default: 비공개
sale_states: [임시저장, 검수 대기, 승인됨]
actions: [새 자산 등록]
```

- `sale_states`: 화면에 나오는 판매 신청 상태. 미션 제출 상태 같은 다른 상태는 `states`에 적는다.
- 운영자 검수 화면은 `checklist`(PRD §6-7 판매 기준 8개를 문장 그대로)와 `review_actions`(승인, 수정 요청, 반려)를 추가로 적는다.

YAML 블록 아래는 자유 서술(레이아웃, 흐름, 의도)이며 판정 대상이 아니다.

### Figma 레이어 이름 규칙
판정 스크립트는 Figma 노드를 이름으로 찾는다. 이름이 다르면 찾지 못해 위반으로 센다.

| 대상 | 이름 |
|---|---|
| 키스크린 프레임 | `key/<화면명>` (실행 페이지 최상위) |
| 완성 시안 프레임 | `screen/<화면명>` (실행 페이지 최상위) |
| 컴포넌트와 인스턴스 | `design.md`의 컴포넌트명 그대로 (`button-primary`, `text-input` 등). 새 컴포넌트는 설계서의 `new:` 이름 |
| 공개 범위 선택 | `visibility-select`, 그 안의 선택된 항목은 `option/selected` |
| 자산 카드 | `asset-card`, 그 안의 공개 범위 표시는 `visibility-label` |
| 판매 상태 표시 | `sale-status` |
| 검수 액션 묶음 | `review-actions`, 그 안의 버튼은 `button-` 컴포넌트 |
| 앱 아이콘 | `app-icon-squircle` |

- 사진, 스크린샷, 브랜드 아이콘 같은 콘텐츠는 이미지 채움으로 넣는다. 이미지 채움만 색 검사에서 빠진다.
