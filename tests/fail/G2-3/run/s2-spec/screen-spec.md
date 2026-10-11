# 화면설계서

## 내 자산

```yaml
screen: 내 자산
stories:
- 4
adopt:
- A-01
- A-02
keyscreen: true
components:
- name: button-primary
- name: text-input
- name: 'new: asset-card'
  visibility_label: true
fields:
- name: 공개 범위
  options:
  - 비공개
  - 멤버 공개
  - 판매 신청
  default: 비공개
sale_states:
- 임시저장
- 검수 대기
- 승인됨
actions:
- 새 자산 등록
```

레이아웃과 흐름 설명.

## 운영자 검수 화면

```yaml
screen: 운영자 검수 화면
stories:
- 5
adopt:
- A-04
- A-05
- A-06
keyscreen: true
components:
- name: button-primary
- name: button-outline
- name: 'new: review-checklist'
checklist:
- 실제 업무에 써본 것
- 결과 예시가 있는 것
- 사용 방법이 명확한 것
- 초보자가 따라할 수 있는 것
- 특정 툴/버전/환경 조건이 적혀 있는 것
- 개인정보/고객정보/회사기밀이 없는 것
- 저작권 문제가 없는 것
- 구매자가 바로 써볼 수 있는 것
review_actions:
- 승인
- 수정 요청
- 반려
sale_states:
- 검수 대기
```

레이아웃과 흐름 설명.
