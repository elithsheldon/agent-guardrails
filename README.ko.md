# agent-guardrails

[English](README.md) · [日本語](README.ja.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · **한국어** · [Français](README.fr.md) · [Español](README.es.md) · [Deutsch](README.de.md) · [Bahasa Indonesia](README.id.md) · [Bahasa Melayu](README.ms.md) · [ไทย](README.th.md)

Claude Code용 **가드레일 훅 모음**. 반복되는 실수를 "다음엔 조심하자"는 메모가 아니라
**기계로 막습니다**.

> 사람의 주의력이 아니라 기계로 보장한다.

## 왜 만들었나

30개 세션, 사용자 발화 887건을 실측했습니다. 사용자가 저를 고쳐준 지점이 **44곳**이었고
6가지 패턴으로 수렴했습니다. 그리고 **그 전부가 "메모에 적어둔 문장"만으로 지켜지고
있었습니다**. 메모는 이미 쓰여 있었고, 실수는 그래도 일어났습니다.

| 실측 횟수 | 패턴 | 현재 방어 |
| --- | --- | --- |
| 12 | 글의 품질 | `reply_check.py`가 검출 |
| 9 | 너무 이른 완료 선언 | `reply_check.py`가 검출 |
| 9 | 요청하지 않은 산출물 제출 | `outward_action_guard.py`가 **거부** |
| 7 | 시도하지 않고 "못 한다"고 말함 | `reply_check.py`가 검출 |
| 4 | 지시 누락 | 기준 파일에 기재(임계값 미만) |
| 3 | 대상 저장소·환경 착오 | 기준 파일에 기재(임계값 미만) |

채택 기준은 **5회 이상 = 반복되고 있다 = 메모로는 못 고친다**입니다. 그 메모는 이미
한 번 실패했습니다. 4회 이하는 문장으로 남깁니다. 전부 차단하면 경고가 포화되어
아무도 읽지 않습니다.

## 구성

### 훅 (`~/.claude/settings.json`에 등록, 모든 디렉터리에서 동작)

| 파일 | 이벤트 | 하는 일 |
| --- | --- | --- |
| `reply_check.py` | Stop | 상태 블록 누락, 근거 없는 완료 주장, 시도 없는 "못 한다", 기계가 쓴 것처럼 읽히는 구문(`X, not Y` 대구, 개수 예고형 도입, 분열문 도입, 뜸들이기), 챗봇 상투어를 검출. **경고만** — Stop에서 막으면 루프 위험 |
| `outward_action_guard.py` | PreToolUse(Bash) | 되돌리기 어려운 외부 동작(PR/push/저장소 생성/릴리스/gist)을 **거부**. 아울러 `<검사> \| tail; echo $?`도 거부 — 그건 검사가 아니라 `tail`의 종료 코드 |
| `guard_the_guards.py` | PreToolUse(Edit/Write) | 검사기·훅·설정·memory를 편집할 때 확인을 요구. **심사받는 쪽이 채점자를 고쳐 쓰는 것**을 방지 |
| `daily-retro-reminder.sh` | PostToolUse | 일일 보고서를 쓰면 회고 절차를 재촉 |

### 스킬

`skills/daily-retro/` — 일일 보고서 작성을 기점으로 하는 개선 루프. 각 실수를 다음
사다리에서 **가능한 한 아래로** 내립니다:

> memory → 문서 → 스크립트 → 사전 검사 → 테스트 → 권한

### 스크립트

| 파일 | 용도 |
| --- | --- |
| `mistake-frequency.py` | 과거 전체 세션에서 교정 패턴을 **셉니다**. "그건 이미 고쳤다"를 인상이 아니라 실측으로 판단하기 위해 |
| `verify-gates.py` | **차단기 자체의 자가 테스트.** 걸려야 할 입력과 걸리면 안 되는 입력을 모두 넣어봅니다 |

### 참고 자료

`reference/anti-self-deception/` — 다른 팀의 성숙한 방어 체계(규칙 24개, 스크립트 15개,
상시 점검 29개). 허락을 받아 익명화하여 수록. 자세한 내용은 `ATTRIBUTION.md`.

## 가장 효과가 컸던 둘

**`guard_the_guards.py`** — 다른 방어는 전부 "산출물"만 보고 있었고,
**심사받는 쪽이 채점자를 고쳐 쓰는 것**을 막는 층이 없었습니다.

**`verify-gates.py`** — 노후 탐지기를 세 번 만들었는데 세 번 다 18건 전부 통과했습니다.
숫자를 읽지 않았다면 세 번 연속 "건강함"이라고 보고했을 것입니다.
**한 번도 실패한 적 없는 검사는 아무것도 지키지 않고 있을 수 있습니다.**

## 설치

클론 후 `bash install.sh`. `~/.claude/hooks/`와 `~/.claude/skills/`에 복사하고
`~/.claude/settings.json`에 훅을 등록합니다(추가만 하며 기존 설정은 보존).

`CLAUDE.example.md`는 내용을 읽고 자신의 환경(memory 경로, 일일 보고서 위치)에
맞춘 뒤 `~/.claude/CLAUDE.md`에 두십시오.

설치 후에는 반드시 자가 테스트를 실행하십시오:

    python3 ~/.claude/skills/daily-retro/scripts/verify-gates.py

신규 환경 21/21, 설정된 환경 26/26으로 통과했습니다.

## 주의

- 훅은 `~/.claude/`에 있으므로 **모든 디렉터리에서 동작**합니다. memory는 그렇지 않고
  Claude를 시작한 디렉터리 단위로 나뉘므로, 프로젝트 공통 원칙은 매번 읽히는
  `~/.claude/CLAUDE.md`에 두십시오.
- `outward_action_guard.py`는 push를 막습니다. 의도한 것은 `CLAUDE_OUTWARD_OK=1`을 붙이고,
  번거로우면 `GUARDED` 목록에서 빼십시오.
- `reply_check.py`는 정규식이라 오탐이 납니다. 오탐이 나면 **지우지 말고 패턴을 좁히십시오.**
- 훅의 런타임 메시지는 현재 일본어입니다. agent가 읽는 것이라 동작에는 영향이 없지만,
  번역 기여를 환영합니다.

## 감사의 말

`reference/anti-self-deception/` 의 규칙·스크립트·상시 점검은
[@Karas-cnk](https://github.com/Karas-cnk) 님의 저작물이며 허락을 받아 수록했습니다. `guard_the_guards.py` 와
`outward_action_guard.py` 의 파이프/종료 코드 규칙은 여기서 이식했습니다.

## 라이선스

MIT
