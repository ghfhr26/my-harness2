# 화면설계서 (S2)

대상 화면: 내 자산, 자산 상세, 운영자 검수 화면 / 유저스토리 3, 4

### 공통 규칙 (세 화면 모두)

- 프레임: 너비 390, 높이 844 이상. 내용이 길면 높이를 늘린다. 좌우 여백은 `{spacing.md}`(16)이고, 프레임 바로 아래 요소는 좌우 16 안에 두거나 좌우를 꽉 채운다.
- 화면마다 프레임은 1개이고, 아래 각 섹션의 "프레임에 그리는 상태"를 그린다. "조건부 상태"는 그 프레임에 그리지 않는다.
- 색은 `docs/design.md`의 색 토큰만 쓴다. 상태 구분도 모노크롬 사다리(`{colors.ink}`, `{colors.canvas-soft}`, `{colors.hairline}`, `{colors.text-muted}`) 안에서 한다. `{colors.accent}`는 세 화면 모두 쓰지 않는다.
- 그림자는 쓰지 않는다. 모서리는 0 / 16 / 24 / 9999만 쓴다. 칩, 배지, 버튼, 체크박스는 전부 `{rounded.full}`이다.
- 버튼(`button-`)과 `text-input`은 높이 48로 그린다(44 미만 금지).
- 판매 신청 상태 배지는 `sale-status` 레이어 1개에 텍스트 노드 1개만 넣고, 글자는 상태명 그대로 적는다(`임시저장`, `검수 대기`, `수정 요청`, `승인됨`, `반려`). 건수나 다른 글자를 붙이지 않는다.
- 필터 칩은 `filter-chip`이라는 이름으로 그린다. `sale-status`로 이름 짓지 않는다(칩에는 건수가 붙는다).
- 더미 텍스트에 이메일, 전화번호, 실존 인물·회사·제품 이름을 넣지 않는다. 사람 이름은 아래에 적힌 별명만 쓴다.
- `판매 중`, `판매 중지`, 가격·구매·수익·정산·허들링 픽 관련 문구는 멤버 화면에 넣지 않는다.

### `sale-status` 배지 모양 (세 화면 공통)

높이 24, 좌우 패딩 `{spacing.sm}`(12), `{rounded.full}`, 글자 `{typography.label}`.

| 상태 | 채움 | 테두리 | 글자색 |
|---|---|---|---|
| 임시저장 | `{colors.canvas}` | 1px `{colors.hairline}` | `{colors.text-muted}` |
| 검수 대기 | `{colors.canvas-soft}` | 없음 | `{colors.ink}` |
| 수정 요청 | `{colors.ink}` | 없음 | `{colors.on-primary}` |
| 승인됨 | `{colors.canvas}` | 1px `{colors.ink}` | `{colors.ink}` |
| 반려 | `{colors.canvas-soft}` | 없음 | `{colors.text-muted}` |

멤버가 손을 대야 하는 `수정 요청`만 잉크 채움으로 가장 진하게 둔다.

### `filter-chip` 모양 (내 자산, 운영자 검수 화면 공통)

높이 44, 좌우 패딩 `{spacing.md}`(16), `{rounded.full}`, 글자 `{typography.link}`. 선택된 칩은 `{colors.ink}` 채움에 `{colors.on-primary}` 글자, 나머지는 `{colors.canvas-soft}` 채움에 `{colors.ink}` 글자. 칩 사이 간격 `{spacing.xs}`(8). 칩 줄은 좌우를 꽉 채운 가로 스크롤 컨테이너(좌우 패딩 16, 넘치는 부분은 잘림)에 넣는다.

## 내 자산

```yaml
screen: 내 자산
stories: [3, 4]
adopt: [A-01, A-02, A-03, A-04, A-05]
keyscreen: true
components:
  - name: button-primary
  - name: "new: filter-chip"
  - name: "new: asset-card"
    visibility_label: true
  - name: "new: sale-status"
  - name: ex-empty-state-card
fields:
  - name: 상태 필터
    options: [전체, 임시저장, 검수 대기, 수정 요청, 승인됨, 반려]
    default: 전체
sale_states: [임시저장, 검수 대기, 수정 요청, 승인됨, 반려]
actions: [새 자산 등록, 상태별로 거르기, 자산 상세 열기]
```

### 프레임에 그리는 상태

판매 승인 회원이 자산 6개를 가진 상태, 필터는 `전체` 선택.

### 레이아웃 (위에서 아래로)

1. 화면 제목 "내 자산" — `{typography.heading-1}`, `{colors.ink}`. 위 여백 `{spacing.section}`(48).
2. 보조 문구 "내가 만든 자료를 모으고, 골라서 판매 신청할 수 있어요." — `{typography.body-lg}`, `{colors.text-muted}`. 제목과 간격 `{spacing.xs}`(8).
3. `button-primary` "새 자산 등록" — 제목 블록 바로 아래 **왼쪽 정렬**, 내용 너비만큼만(꽉 채우지 않는다), 높이 48. 위 간격 `{spacing.md}`(16). 목록이 비어 있든 길든 이 자리는 그대로다. (A-02)
4. 필터 칩 줄 — `filter-chip` 6개를 한 줄로. 위 간격 `{spacing.lg}`(24). 칩 글자는 상태 이름 뒤에 건수를 붙인다: `전체 6`, `임시저장 2`, `검수 대기 1`, `수정 요청 1`, `승인됨 1`, `반려 1`. `전체 6`만 선택(채움) 상태다. (A-01, A-03)
5. 자산 카드 목록 — `asset-card` 6개를 세로로, 카드 사이 간격 `{spacing.sm}`(12). 위 간격 `{spacing.md}`(16). 목록 아래 여백 `{spacing.section}`(48).

### `asset-card`

- `{colors.canvas}` 채움, 1px `{colors.hairline-soft}` 테두리, `{rounded.md}`(24), 패딩 `{spacing.md}`(16), 너비 358.
- 안쪽 순서(세로, 간격 `{spacing.xs}` 8):
  1. 분류 — `{typography.caption}`, `{colors.text-muted}`
  2. 제목 — `{typography.title}`, `{colors.ink}`, 한 줄
  3. 설명 한 줄 — `{typography.body-sm}`, `{colors.text-muted}`, 넘치면 말줄임
  4. 맨 아래 줄(위 간격 `{spacing.sm}` 12): 왼쪽 끝에 `sale-status` 배지 1개, 오른쪽 끝에 `visibility-label`
- `sale-status`는 모든 카드에서 맨 아래 줄 왼쪽 끝, 같은 위치에 둔다. 카드마다 1개. (A-05)
- `visibility-label`은 텍스트 레이어 1개다. 글자는 `비공개`, `멤버 공개`, `판매 신청` 중 하나만, `{typography.caption}`, `{colors.text-muted}`. 카드마다 정확히 1개. 앞에 "공개 범위" 같은 다른 글자를 붙이지 않는다.
- 카드를 누르면 자산 상세로 간다.

### 더미 텍스트

| 분류 | 제목 | 설명 | sale-status | visibility-label |
|---|---|---|---|---|
| 스킬 파일 | QA 자동화 스킬 파일 | 테스트 케이스와 버그 리포트 초안을 만들어 줘요 | 수정 요청 | 판매 신청 |
| 프롬프트 | 주간 회의록 요약 프롬프트 | 녹취 메모를 결정 사항과 할 일로 나눠요 | 검수 대기 | 판매 신청 |
| 자동화 템플릿 | 견적서 자동 작성 템플릿 | 문의 내용을 표로 정리해 견적서 초안을 채워요 | 승인됨 | 판매 신청 |
| 프롬프트 | 뉴스레터 초안 프롬프트 모음 | 주제 한 줄로 제목 후보와 본문 틀을 뽑아요 | 반려 | 판매 신청 |
| 업무 적용 사례 | 고객 문의 분류 자동화 사례 | 문의를 유형별로 나눠 응대 시간을 줄인 기록 | 임시저장 | 멤버 공개 |
| 자동화 템플릿 | 온보딩 체크리스트 템플릿 | 새 팀원 첫 주 할 일을 자동으로 만들어요 | 임시저장 | 비공개 |

### 조건부 상태 (프레임에 그리지 않음)

- **빈 상태** (A-04): 제목, 보조 문구, "새 자산 등록" 버튼, 칩 줄(건수 전부 0)은 그대로 두고, 목록 자리 가운데에 `ex-empty-state-card`를 둔다. `{colors.canvas-soft}` 채움, `{rounded.md}`, 패딩 `{spacing.lg}`. 안에는 안내 한 줄 "아직 등록한 자산이 없어요" (`{typography.body}`, `{colors.text-muted}`)와 `button-primary` "새 자산 등록" 1개만 둔다. 일러스트는 넣지 않는다. 이 버튼도 새 자산 등록으로 이어진다.
- **필터 결과 없음**: 선택한 상태의 자산이 0개면 목록 자리에 "이 상태의 자산이 없어요" 한 줄만 둔다. 버튼은 없다.
- **유료 회원(판매 승인 전)**: 카드의 `visibility-label`은 `비공개` 또는 `멤버 공개`만 나오고 `sale-status`는 전부 `임시저장`이다.

### 흐름

- "새 자산 등록" → 새 자산 작성. 새로 만든 자산의 공개 범위는 `비공개`, 판매 신청 상태는 `임시저장`으로 시작한다.
- 카드 → 자산 상세.

### 미정

- 새 자산 등록이 어느 화면에서 이뤄지는지(파일 첨부, 설명 작성 입력 폼). PRD §16 핵심 화면 10개에 등록 화면이 따로 없다. 이 설계서는 등록 폼을 그리지 않는다.
- 판매 신청을 하지 않은 자산(`비공개`, `멤버 공개`)에 판매 신청 상태를 보여 줄지. PRD 데이터 모델의 `review_status: draft`를 근거로 `임시저장`으로 표시했다.
- 반려된 자산의 공개 범위가 `판매 신청`으로 남는지 `비공개`로 돌아가는지. 더미에서는 `판매 신청`으로 두었다.
- 앱 전체 내비게이션(탭 바 등). `docs/design.md`에 모바일 앱 내비게이션 규칙이 없어 이 화면에는 넣지 않았다.

## 자산 상세

```yaml
screen: 자산 상세
stories: [3, 4]
adopt: [A-06, A-07, A-08, A-09, A-10]
keyscreen: true
components:
  - name: button-pill-soft
  - name: "new: tag-chip"
  - name: "new: sale-status"
  - name: "new: review-notice"
  - name: "new: visibility-select"
    visibility_label: true
  - name: "new: file-row"
  - name: button-outline
  - name: button-primary
fields:
  - name: 공개 범위
    options: [비공개, 멤버 공개, 판매 신청]
    default: 비공개
sale_states: [임시저장, 검수 대기, 수정 요청, 승인됨, 반려]
actions: [내 자산으로 돌아가기, 공개 범위 바꾸기, 수정, 판매 신청]
```

### 프레임에 그리는 상태

판매 승인 회원이 방금 등록한 자산을 보는 상태. 공개 범위는 기본값 `비공개`, 판매 신청 상태는 `임시저장`. 멤버 본인이 보는 화면이다.

### 레이아웃 (위에서 아래로)

1. 상단 줄 — 왼쪽에 `button-pill-soft` "← 내 자산" (높이 44). 위 여백 `{spacing.md}`(16).
2. 미리보기 — 너비 358, 높이 200, `{rounded.md}`(24). 이미지 채움으로 넣는다(자산 결과 예시 스크린샷). 위 간격 `{spacing.md}`(16).
3. 제목 "온보딩 체크리스트 템플릿" — `{typography.heading-2}`, `{colors.ink}`. 위 간격 `{spacing.lg}`(24).
4. 태그 줄 — `tag-chip` 3개를 가로로, 간격 `{spacing.xs}`(8). 위 간격 `{spacing.sm}`(12). (2~4가 A-10의 "미리보기, 제목, 태그 줄" 순서다)
5. 판매 신청 상태 블록 — 위 간격 `{spacing.lg}`(24). 세로로, 간격 `{spacing.xs}`(8).
   1. `sale-status` 배지 "임시저장"
   2. 굵은 한 줄 "아직 판매 신청 전이에요" — `{typography.heading-4}`, `{colors.ink}` (A-08)
   3. 보조 문구 "판매 신청을 하면 운영자 검수를 거친 뒤 승인돼요." — `{typography.body-sm}`, `{colors.text-muted}` (A-08)
   4. (조건부) `review-notice` — `수정 요청`, `반려` 상태에서만 이 자리에 붙는다. 이 프레임에는 그리지 않는다. (A-07)
6. 공개 범위 줄 `visibility-select` — 위 간격 `{spacing.lg}`(24). (A-06)
7. 공개 범위 설명 — `visibility-select` 바로 아래, 간격 `{spacing.xs}`(8). (A-09)
8. 섹션 "설명" — 섹션 제목 `{typography.heading-4}`, 본문 `{typography.body}` `{colors.ink}`. 위 간격 `{spacing.xl}`(32), 제목과 본문 간격 `{spacing.xs}`(8).
9. 섹션 "포함 파일" — 섹션 제목 `{typography.heading-4}`, 그 아래 `file-row` 2개, 간격 `{spacing.xs}`(8). 위 간격 `{spacing.xl}`(32). 아래에 하단 바에 가리지 않도록 여백 `{spacing.section}`(48)을 둔다.
10. 하단 고정 바 — 프레임 맨 아래, 좌우를 꽉 채움. (A-10)

### `visibility-select` (A-06)

- 한 줄짜리 행. `{colors.canvas-soft}` 채움, `{rounded.sm}`(16), 패딩 `{spacing.sm} {spacing.md}`(12 / 16), 높이 48 이상, 너비 358.
- 왼쪽: 레이블 "공개 범위" — `{typography.body}`, `{colors.ink}`.
- 오른쪽: 현재 값 + 꺾쇠(›). 현재 값은 `option/selected`라는 이름의 레이어로 감싸고, 그 안에 `visibility-label`이라는 이름의 텍스트 레이어 1개를 둔다. 글자는 정확히 `비공개` — `{typography.title}`, `{colors.ink}`. 꺾쇠는 `option/selected` 밖에 둔다(`{colors.text-faint}`).
- 이 화면에 `visibility-label`은 이것 1개뿐이다. 다른 곳에 공개 범위 글자를 반복하지 않는다.
- 현재 값은 늘 보이고, 본인이 이 줄을 눌러 고를 때만 바뀐다. 다른 동작(수정 저장 등)으로 공개 범위가 바뀌지 않는다.
- 선택지: `비공개`, `멤버 공개`, `판매 신청`. 기본값 `비공개`. `판매 신청`은 판매 승인 회원에게만 선택 가능하다.

### 공개 범위 설명 (A-09)

`{typography.body-sm}`, `{colors.text-muted}`. 세 줄, 줄마다 텍스트 레이어를 나누지 않고 한 덩어리로 둔다.

```
비공개는 나만 볼 수 있어요.
멤버 공개는 허들링 멤버에게 보여요.
판매 신청은 운영자 검수를 통과해야 승인돼요.
```

### `tag-chip`

높이 24, 좌우 패딩 `{spacing.sm}`(12), `{colors.canvas-soft}` 채움, `{rounded.full}`, 글자 `{typography.label}` `{colors.ink}`. 누를 수 없는 표시용이다. 더미: `자동화 템플릿`, `온보딩`, `체크리스트`.

### `file-row`

`{colors.canvas}` 채움, 1px `{colors.hairline-soft}` 테두리, `{rounded.sm}`(16), 패딩 `{spacing.sm} {spacing.md}`. 왼쪽 파일명 `{typography.body}` `{colors.ink}`, 오른쪽 용량 `{typography.caption}` `{colors.text-muted}`. 더미: `온보딩-체크리스트-템플릿.md` · `12KB`, `사용-방법.pdf` · `340KB`.

### 하단 고정 바 (A-10)

- `{colors.canvas}` 채움, 위쪽에 1px `{colors.hairline-soft}` 선, 패딩 `{spacing.md}`(16), 그림자 없음. 스크롤과 무관하게 화면 아래에 붙는다.
- 버튼 2개를 가로로 같은 너비, 간격 `{spacing.xs}`(8), 높이 48.
  - 왼쪽 `button-outline` "수정" — 설명과 첨부 파일을 고친다.
  - 오른쪽 `button-primary` "판매 신청" — 공개 범위에서 `판매 신청`을 고르는 것과 같은 동작이다. 판매 승인 회원에게만 보인다.
- 가격, 구매, 다운로드 수 같은 것은 넣지 않는다.

### 더미 텍스트

- 제목: 온보딩 체크리스트 템플릿
- 설명: "새 팀원이 들어오면 첫 주에 할 일을 역할별 체크리스트로 만들어 주는 자동화 템플릿이에요. 직무와 입사일만 넣으면 표가 채워져요."

### 조건부 상태 (프레임에 그리지 않음)

판매 신청 상태 블록(레이아웃 5번)은 상태에 따라 아래처럼 바뀐다. 공개 범위 줄의 현재 값은 `검수 대기` 이후로 `판매 신청`이다.

| sale-status | 굵은 한 줄 | 보조 문구 | review-notice | 하단 바 |
|---|---|---|---|---|
| 임시저장 | 아직 판매 신청 전이에요 | 판매 신청을 하면 운영자 검수를 거친 뒤 승인돼요. | 없음 | 수정 / 판매 신청 |
| 검수 대기 | 운영자 검수를 기다리고 있어요 | 검수가 끝나면 결과를 알림으로 알려 드려요. | 없음 | 수정 |
| 수정 요청 | 운영자가 수정을 요청했어요 | 아래 내용을 고친 뒤 다시 신청하면 검수가 이어져요. | 수정 요청 코멘트 | 수정 / 다시 신청 |
| 승인됨 | 판매 신청이 승인됐어요 | 운영자 검수를 통과했어요. | 없음 | 수정 |
| 반려 | 판매 신청이 반려됐어요 | 아래 사유를 확인해 주세요. | 반려 사유 | 수정 |

- `review-notice` (A-07): `sale-status`와 문구 바로 아래, 간격 `{spacing.sm}`(12). `{colors.canvas-soft}` 채움, `{rounded.sm}`(16), 패딩 `{spacing.md}`(16), 테두리 없음. 안에 작은 제목 "운영자 코멘트" 또는 "반려 사유" (`{typography.label}`, `{colors.text-muted}`)와 본문(`{typography.body-sm}`, `{colors.ink}`). 더미: "사용 방법에 필요한 도구 버전이 빠져 있어요. 어떤 환경에서 써 봤는지 적어 주세요."
- 검수 소요 시간은 어느 상태에서도 약속하지 않는다.
- **유료 회원(판매 승인 전)**: 공개 범위 선택지에서 `판매 신청`은 비활성이고 하단 바에 "판매 신청" 버튼이 없다. 보조 문구는 "판매 신청은 판매 승인 회원만 할 수 있어요."

### 흐름

- "← 내 자산" → 내 자산.
- `visibility-select`를 누르면 선택지 3개가 열리고, 고르면 현재 값이 바뀐다.
- "판매 신청"을 누르면 공개 범위가 `판매 신청`, 판매 신청 상태가 `검수 대기`가 되고 운영자 검수 화면의 검수 대기 목록에 올라간다. 검수를 거치지 않고 `승인됨`이 되는 길은 없다.

### 미정

- 공개 범위 선택지가 열리는 방식(바텀시트, 펼침 등). 레퍼런스와 `docs/design.md`에 근거가 없어 그리지 않았다.
- 하단 바의 "판매 신청" 버튼. PRD §6-5에는 공개 범위 선택지로만 나온다. 같은 동작의 바로가기로 두었다.
- `멤버 공개`가 유료 멤버에게만 보이는지 무료 회원에게도 보이는지. PRD에 범위가 없어 설명 문구를 "허들링 멤버"로 적었다.
- `수정 요청` 뒤 다시 신청하는 동작("다시 신청")의 이름과 절차. PRD에 없다.
- `검수 대기`, `승인됨` 상태에서 수정을 허용하는지. PRD에 없다. 표에는 "수정"을 남겨 두었다.
- 멤버가 판매 신청할 때 가격을 적는지. PRD §3-4에는 가격이 언급되지만 §6-5 필수 기능에 가격 입력이 없어 이 화면에 넣지 않았다.
- 운영자가 검수하며 보는 자산 상세(PRD §16 "운영자 검수 상세용")의 차이. 이 프레임은 멤버 본인 화면이다.

## 운영자 검수 화면

```yaml
screen: 운영자 검수 화면
stories: [4]
adopt: [A-11, A-12, A-13, A-14]
keyscreen: true
components:
  - name: "new: filter-chip"
  - name: "new: review-row"
  - name: "new: sale-status"
  - name: button-pill-soft
  - name: "new: checklist-row"
  - name: text-input
  - name: "new: review-actions"
  - name: button-primary
  - name: button-outline
fields:
  - name: 상태 필터
    options: [검수 대기, 수정 요청, 승인됨, 반려]
    default: 검수 대기
  - name: 검수 코멘트
  - name: 판매 가격
sale_states: [검수 대기, 수정 요청, 승인됨, 반려]
checklist:
  - 실제 업무에 써본 것
  - 결과 예시가 있는 것
  - 사용 방법이 명확한 것
  - 초보자가 따라할 수 있는 것
  - 특정 툴/버전/환경 조건이 적혀 있는 것
  - 개인정보/고객정보/회사기밀이 없는 것
  - 저작권 문제가 없는 것
  - 구매자가 바로 써볼 수 있는 것
review_actions: [승인, 수정 요청, 반려]
actions: [상태별로 거르기, 검수할 자산 고르기, 자산 상세 보기, 판매 기준 체크, 코멘트 작성, 가격 입력, 승인, 수정 요청, 반려]
```

### 프레임에 그리는 상태

운영자가 `검수 대기` 필터에서 첫 번째 자산을 골라 검수하는 중. 판매 기준 8개 중 5개를 체크했고, "승인" 버튼은 비활성이다.

### 레이아웃 (위에서 아래로)

1. 화면 제목 "판매 신청 검수" — `{typography.heading-1}`, `{colors.ink}`. 위 여백 `{spacing.section}`(48).
2. 필터 칩 줄 — `filter-chip` 4개: `검수 대기 3`, `수정 요청 1`, `승인됨 4`, `반려 1`. `검수 대기 3`만 선택(채움) 상태다. 화면에 들어오면 늘 `검수 대기`가 먼저 선택돼 있다. 위 간격 `{spacing.lg}`(24). (A-14)
3. 검수 대기 목록 — `review-row` 3개를 세로로, 간격 `{spacing.xs}`(8). 위 간격 `{spacing.md}`(16). 첫 번째 행이 선택된 상태다. (A-13)
4. 검수 패널 — 위 간격 `{spacing.xl}`(32). 아래 순서로 세로로 쌓는다.
   1. 섹션 제목 "검수 중인 자산" — `{typography.heading-4}`.
   2. 자산 제목 "주간 회의록 요약 프롬프트" (`{typography.title}`)와 오른쪽 끝 `button-pill-soft` "자산 상세 보기" (높이 44). 간격 `{spacing.xs}`(8).
   3. 섹션 제목 "판매 기준 체크리스트" — `{typography.heading-4}`. 위 간격 `{spacing.lg}`(24). 오른쪽에 진행 표시 "5/8" (`{typography.caption}`, `{colors.text-muted}`).
   4. `checklist-row` 8개 — 세로로, 간격 `{spacing.xxs}`(4). 위 간격 `{spacing.xs}`(8). (A-11)
   5. `text-input` "검수 코멘트" — 위 간격 `{spacing.lg}`(24). 위에 레이블 "검수 코멘트" (`{typography.label}`, `{colors.text-muted}`), 입력란 자리 표시 "수정 요청이나 반려 때 멤버에게 전달할 내용을 적어요" (`{colors.text-faint}`). 여러 줄, 높이 96.
   6. `text-input` "판매 가격" — 위 간격 `{spacing.md}`(16). 위에 레이블 "판매 가격" (`{typography.label}`, `{colors.text-muted}`), 입력란 자리 표시 "원 단위로 입력" (`{colors.text-faint}`). 높이 48.
   7. 안내 한 줄 "판매 기준 8개를 모두 체크해야 승인할 수 있어요" — `{typography.caption}`, `{colors.text-muted}`. 위 간격 `{spacing.lg}`(24).
   8. `review-actions` — 위 간격 `{spacing.xs}`(8). 아래 여백 `{spacing.section}`(48).

### `review-row` (A-13)

- 가로 배치. `{rounded.sm}`(16), 패딩 `{spacing.sm}`(12), 너비 358. 선택된 행은 `{colors.canvas-soft}` 채움에 테두리 없음, 나머지는 `{colors.canvas}` 채움에 1px `{colors.hairline-soft}` 테두리.
- 왼쪽: 썸네일 72×72, `{rounded.sm}`(16), 이미지 채움.
- 오른쪽(간격 `{spacing.sm}` 12, 세로로 간격 `{spacing.xxs}` 4), 이 순서로:
  1. 분류 — `{typography.caption}`, `{colors.text-muted}`
  2. 제목 — `{typography.title}`, `{colors.ink}`
  3. 요약 두 줄 — `{typography.body-sm}`, `{colors.text-muted}`, 두 줄에서 말줄임
  4. 메타 — `{typography.caption}`, `{colors.text-faint}` (신청자 별명 · 신청일)
  5. `sale-status` 배지 — 행 맨 아래. 위 간격 `{spacing.xs}`(8)
- 이 행은 자산 카드가 아니다. `asset-card`로 이름 짓지 않고, `visibility-label`도 넣지 않는다.

### `checklist-row` (A-11)

- 한 줄에 왼쪽 체크박스, 오른쪽 기준 문장. 높이 44 이상, 간격 `{spacing.sm}`(12). 문장이 길면 줄바꿈한다.
- 체크박스: 24×24, `{rounded.full}`.
  - 체크함: `{colors.ink}` 채움 + `{colors.on-primary}` 체크 표시. 문장은 `{typography.body}`, `{colors.ink}`.
  - 체크 안 함: `{colors.canvas}` 채움 + 1px `{colors.hairline}` 테두리, 표시 없음. 문장은 `{typography.body}`, `{colors.text-muted}`.
- 취소선은 쓰지 않는다(체크는 "확인함"이지 "지움"이 아니다).
- 기준 문장은 항목마다 텍스트 레이어 1개에 아래 글자 그대로 적는다. 번호, 마침표, 줄임을 넣지 않는다.
- "모두 체크" 같은 일괄 체크는 두지 않는다. 항목을 하나씩 확인한다.

| 순서 | 기준 문장 (그대로) | 프레임에서 |
|---|---|---|
| 1 | 실제 업무에 써본 것 | 체크함 |
| 2 | 결과 예시가 있는 것 | 체크함 |
| 3 | 사용 방법이 명확한 것 | 체크함 |
| 4 | 초보자가 따라할 수 있는 것 | 체크함 |
| 5 | 특정 툴/버전/환경 조건이 적혀 있는 것 | 체크 안 함 |
| 6 | 개인정보/고객정보/회사기밀이 없는 것 | 체크함 |
| 7 | 저작권 문제가 없는 것 | 체크 안 함 |
| 8 | 구매자가 바로 써볼 수 있는 것 | 체크 안 함 |

### `review-actions` (A-12)

- 레이어 이름 `review-actions`. 안에 버튼은 정확히 3개이고, 다른 버튼을 넣지 않는다. 라벨은 `승인`, `수정 요청`, `반려` 그대로.
- 배치: 첫 줄에 `button-primary` "승인"을 좌우 꽉 채워, 둘째 줄에 `button-outline` "수정 요청"과 `button-outline` "반려"를 같은 너비로 나란히. 줄 간격과 버튼 간격 `{spacing.xs}`(8), 버튼 높이 48.
- "승인"은 판매 기준 8개가 전부 체크되기 전에는 비활성이다. 이 프레임은 5/8이라 비활성으로 그린다: `{colors.canvas-soft}` 채움, 라벨 `{colors.text-faint}`, 테두리 없음. 8개가 전부 체크되면 `{colors.primary}` 채움에 `{colors.on-primary}` 라벨로 바뀐다.
- "수정 요청"과 "반려"는 체크 수와 관계없이 누를 수 있다.

### 더미 텍스트

`review-row` 3개. 전부 `sale-status`는 `검수 대기`.

| 분류 | 제목 | 요약 | 메타 |
|---|---|---|---|
| 프롬프트 | 주간 회의록 요약 프롬프트 | 녹취 메모를 결정 사항과 할 일로 나눠 정리해요. 회의 유형별 예시 3개가 들어 있어요. | 달빛토끼 · 2026.10.08 신청 |
| 스킬 파일 | 릴리스 노트 작성 스킬 파일 | 변경 기록을 읽어 사용자용 릴리스 노트 초안을 만들어요. 설치 방법과 사용 예시 포함. | 초록연필 · 2026.10.09 신청 |
| 자동화 템플릿 | 설문 응답 정리 템플릿 | 주관식 응답을 주제별로 묶고 요약 표를 채워요. 응답 100건 기준으로 써 본 사례 포함. | 느린거북 · 2026.10.10 신청 |

### 조건부 상태 (프레임에 그리지 않음)

- **검수 대기 없음**: 목록 자리에 "검수를 기다리는 자산이 없어요" 한 줄(`{typography.body}`, `{colors.text-muted}`)만 두고 검수 패널은 숨긴다.
- **8개 전부 체크**: 진행 표시 "8/8", 안내 한 줄은 숨기고 "승인" 버튼이 활성으로 바뀐다.
- **다른 필터**(`수정 요청`, `승인됨`, `반려`): 같은 `review-row`에 해당 `sale-status`가 붙는다. 이미 처리된 자산의 검수 패널은 읽기 전용이다.

### 흐름

- 화면에 들어오면 `검수 대기` 필터가 선택돼 있다 → 행을 고른다 → "자산 상세 보기"로 내용을 확인한다 → 체크리스트를 하나씩 체크한다 → 승인 / 수정 요청 / 반려.
- 승인 → 그 자산의 판매 신청 상태가 `승인됨`. 수정 요청 → `수정 요청`, 코멘트가 멤버의 자산 상세 `review-notice`에 나온다. 반려 → `반려`, 사유가 같은 자리에 나온다.
- 결과는 멤버의 내 자산 카드 `sale-status`와 자산 상세에 반영된다. 이번 범위의 마지막 상태는 `승인됨`이다.

### 미정

- 비활성 버튼의 모양. `docs/design.md`에 비활성 상태 규칙이 없어 색 토큰 안에서 `{colors.canvas-soft}` 채움 + `{colors.text-faint}` 라벨로 정했다.
- 체크박스 컴포넌트. `docs/design.md`에 없어 `checklist-row` 안에 새로 정했다.
- 반려 사유 입력. PRD §6-7에는 "수정 요청 코멘트 작성"만 있다. 반려 사유도 같은 "검수 코멘트" 입력란에 적는 것으로 두었다.
- 수정 요청·반려 때 코멘트가 필수인지. PRD에 없다.
- 판매 가격을 누가 먼저 적는지(멤버가 신청하며 제안하는지, 운영자가 정하는지). PRD §6-7은 "가격 설정 또는 가격 승인"이라고만 한다. 운영자가 입력하는 빈 입력란 1개로 두었다.
- 판매 회원 수동 승인(PRD §6-7 9번). 회원 역할을 바꾸는 기능이라 검수 흐름과 다른 화면이 필요하다. 이 화면에 넣지 않았다.
- 목록과 검수 패널을 한 화면에 쌓을지, 행을 눌러 다른 화면으로 갈지. 대상 화면이 1개라 한 프레임에 쌓았다.
