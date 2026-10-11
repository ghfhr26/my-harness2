# 화면설계서

## 내 자산

```yaml
screen: 내 자산
stories:
- 4
adopt:
- A-01
- A-02
- A-03
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
