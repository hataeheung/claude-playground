# ACB - Agentic Coding Bot

에이전틱 코딩 프로세스를 체계적으로 가이드하는 개인 어시스턴트 봇입니다.

## 왜 필요한가?

AI와 함께 코딩할 때 체계적인 프로세스 없이 바로 구현에 뛰어들면:
- 요구사항을 놓치거나 잘못 이해함
- 기존 코드를 읽지 않고 수정하여 버그 발생
- 불필요한 복잡성 추가
- 검증 없이 배포하여 장애 발생

ACB는 6단계 프로세스를 따라가도록 가이드하여 이런 문제를 예방합니다.

## 프로세스 (6단계)

```
ANALYZE → EXPLORE → PLAN → IMPLEMENT → VERIFY → DELIVER
```

| 단계 | 핵심 질문 | 산출물 |
|------|-----------|--------|
| **ANALYZE** | 무엇을 만들어야 하는가? | 요구사항, 성공 기준 |
| **EXPLORE** | 현재 상태는 어떠한가? | 파일 목록, 아키텍처 메모 |
| **PLAN** | 어떻게 만들 것인가? | TODO 목록, 구현 순서 |
| **IMPLEMENT** | 코드를 작성한다 | 코드, 검증 결과 |
| **VERIFY** | 제대로 동작하는가? | 테스트 결과, 리뷰 |
| **DELIVER** | 변경사항을 전달한다 | 커밋, PR |

## 설치 및 실행

```bash
# 의존성 설치
pip install -e .

# 실행
acb
```

## 사용법

### 기본 흐름

```
$ acb

  Agentic Coding Bot
  에이전틱 코딩 프로세스 어시스턴트

새로운 코딩 세션을 시작합니다.
어떤 작업을 하려고 하시나요?

Task > 사용자 인증 API 구현
```

### 주요 명령어

| 명령어 | 설명 |
|--------|------|
| `next` / `prev` | 다음/이전 단계 이동 |
| `goto <N>` | N번 단계로 이동 (1-6) |
| `check <N>` | 체크리스트 N번 항목 토글 |
| `note <text>` | 현재 단계에 메모 추가 |
| `task <text>` | 작업 항목 추가 |
| `done <N>` | 작업 N번 완료 토글 |
| `status` | 전체 진행 상황 보기 |
| `guide` | 현재 단계 상세 가이드 |
| `export` | 마크다운으로 보고서 출력 |
| `save` / `load` | 세션 저장/로드 |
| `help` | 전체 명령어 보기 |

### 예시 워크플로우

```bash
# 1. ANALYZE 단계
[ANALYZE] > note 사용자 로그인/회원가입 API 필요
[ANALYZE] > note JWT 토큰 기반 인증
[ANALYZE] > check 0    # 요구사항 확인
[ANALYZE] > check 4    # 완료 기준 정의
[ANALYZE] > next

# 2. EXPLORE 단계
[EXPLORE] > note src/auth/ 디렉토리에 기존 인증 코드 존재
[EXPLORE] > check 0    # 프로젝트 구조 파악
[EXPLORE] > next

# 3. PLAN 단계
[PLAN] > task User 모델 정의
[PLAN] > task 로그인 엔드포인트 구현
[PLAN] > task JWT 미들웨어 구현
[PLAN] > task 테스트 작성
[PLAN] > next

# 4~6. 구현, 검증, 전달...
```

## 프로젝트 구조

```
claude-playground/
├── acb/
│   ├── __init__.py      # 패키지 초기화
│   ├── cli.py           # CLI 메인 인터페이스
│   ├── display.py       # Rich 기반 터미널 UI
│   └── process.py       # 프로세스 엔진 및 상태 관리
├── templates/
│   ├── CLAUDE.md.template        # CLAUDE.md 템플릿
│   └── session_report.md.template # 세션 보고서 템플릿
├── PROCESS.md           # 프로세스 상세 문서
├── pyproject.toml       # 프로젝트 설정
└── README.md
```

## 상세 프로세스 문서

각 단계의 상세 체크리스트와 가이드는 [PROCESS.md](./PROCESS.md)를 참고하세요.
