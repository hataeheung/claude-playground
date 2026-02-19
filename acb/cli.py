"""CLI 메인 진입점 - 인터랙티브 에이전틱 코딩 어시스턴트"""

import sys

from acb.display import (
    console,
    show_banner,
    show_checklist,
    show_current_phase,
    show_export,
    show_guide,
    show_help,
    show_notes,
    show_phase_progress,
    show_tasks,
)
from acb.process import PHASE_ORDER, Session, SessionStore


def run_auto_mode(args: list[str]):
    """자율 에이전트 모드 실행

    사용법:
        acb auto "사용자 인증 API 구현"
        acb auto --no-confirm "버그 수정: 로그인 실패"
        acb auto --no-push --no-pr "리팩토링: 코드 정리"
        acb auto init  (설정 초기화)
    """
    from acb.config import load_config, save_config

    config = load_config()

    if not args:
        console.print("[red]사용법: acb auto <요구사항>[/red]")
        console.print("[dim]예: acb auto \"사용자 인증 API 구현\"[/dim]")
        console.print("[dim]    acb auto init  (설정 초기화)[/dim]")
        sys.exit(1)

    # 설정 초기화 명령
    if args[0] == "init":
        _init_config(config)
        save_config(config)
        console.print("[green]설정이 저장되었습니다.[/green]")
        return

    # 옵션 파싱
    requirement_parts = []
    for arg in args:
        if arg == "--no-confirm":
            config.require_confirmation = False
        elif arg == "--no-push":
            config.auto_push = False
        elif arg == "--no-pr":
            config.auto_pr = False
        elif arg == "--no-commit":
            config.auto_commit = False
        elif arg == "--deploy":
            config.auto_deploy = True
        else:
            requirement_parts.append(arg)

    requirement = " ".join(requirement_parts)
    if not requirement:
        console.print("[red]요구사항을 입력해주세요.[/red]")
        sys.exit(1)

    # 에이전트 실행
    from acb.agent import DevAgent
    agent = DevAgent(config=config, project_root=".")
    state = agent.run(requirement)

    sys.exit(0 if state.is_complete else 1)


def _init_config(config):
    """대화형 설정 초기화"""
    console.print("\n[bold]에이전트 설정 초기화[/bold]\n")

    config.project.language = console.input(
        "[cyan]프로그래밍 언어[/cyan] (예: python): "
    ).strip() or config.project.language

    config.project.framework = console.input(
        "[cyan]프레임워크[/cyan] (예: fastapi): "
    ).strip() or config.project.framework

    config.project.test_command = console.input(
        "[cyan]테스트 명령어[/cyan] (예: pytest): "
    ).strip() or config.project.test_command

    config.project.lint_command = console.input(
        "[cyan]린트 명령어[/cyan] (예: ruff check .): "
    ).strip() or config.project.lint_command

    config.project.build_command = console.input(
        "[cyan]빌드 명령어[/cyan] (예: python -m build): "
    ).strip() or config.project.build_command

    config.project.deploy_command = console.input(
        "[cyan]배포 명령어[/cyan] (비워두면 배포 건너뜀): "
    ).strip() or config.project.deploy_command

    config.base_branch = console.input(
        "[cyan]기본 브랜치[/cyan] (기본: main): "
    ).strip() or config.base_branch


def prompt_task_name() -> str:
    console.print()
    console.print("[bold]새로운 코딩 세션을 시작합니다.[/bold]")
    console.print("[dim]어떤 작업을 하려고 하시나요?[/dim]")
    console.print()
    name = console.input("[bold cyan]Task > [/bold cyan]").strip()
    if not name:
        console.print("[red]작업 이름을 입력해주세요.[/red]")
        return prompt_task_name()
    return name


def show_dashboard(session: Session):
    """메인 대시보드"""
    console.clear()
    show_banner()
    console.print(f"[bold]Task:[/bold] {session.task_name}")
    console.print()
    show_phase_progress(session)
    show_current_phase(session)
    show_checklist(session)


def handle_command(cmd: str, session: Session, store: SessionStore) -> bool:
    """명령어 처리. True를 반환하면 대시보드 새로고침."""
    parts = cmd.strip().split(maxsplit=1)
    if not parts:
        return False

    command = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    if command in ("quit", "exit", "q"):
        store.save(session)
        console.print("[dim]세션이 저장되었습니다. 안녕히 가세요![/dim]")
        sys.exit(0)

    elif command == "auto":
        if arg:
            run_auto_mode(arg.split())
        else:
            console.print("[red]사용법: auto <요구사항>[/red]")
        return False

    elif command == "help":
        show_help()
        return False

    elif command == "next":
        result = session.advance_phase()
        if result:
            store.save(session)
            return True
        else:
            console.print("[yellow]이미 마지막 단계입니다.[/yellow]")
            return False

    elif command == "prev":
        result = session.go_back_phase()
        if result:
            store.save(session)
            return True
        else:
            console.print("[yellow]이미 첫 번째 단계입니다.[/yellow]")
            return False

    elif command == "goto":
        try:
            n = int(arg)
            if 1 <= n <= 6:
                session.current_phase = PHASE_ORDER[n - 1]
                session.updated_at = __import__("datetime").datetime.now().isoformat()
                store.save(session)
                return True
            else:
                console.print("[red]1-6 사이의 숫자를 입력해주세요.[/red]")
        except ValueError:
            console.print("[red]숫자를 입력해주세요. (예: goto 3)[/red]")
        return False

    elif command == "status":
        show_phase_progress(session)
        return False

    elif command == "check":
        try:
            n = int(arg)
            if session.check_item(session.current_phase, n):
                store.save(session)
                return True
            else:
                console.print("[red]잘못된 번호입니다.[/red]")
        except ValueError:
            console.print("[red]번호를 입력해주세요. (예: check 0)[/red]")
        return False

    elif command == "checklist":
        show_checklist(session)
        return False

    elif command == "note":
        if arg:
            session.add_note(arg)
            store.save(session)
            console.print("[green]메모가 추가되었습니다.[/green]")
        else:
            console.print("[red]메모 내용을 입력해주세요. (예: note API 구조 파악 완료)[/red]")
        return False

    elif command == "notes":
        show_notes(session, arg if arg else None)
        return False

    elif command == "task":
        if arg:
            session.add_task(arg)
            store.save(session)
            console.print("[green]작업이 추가되었습니다.[/green]")
        else:
            console.print("[red]작업 내용을 입력해주세요. (예: task API 엔드포인트 구현)[/red]")
        return False

    elif command == "tasks":
        show_tasks(session)
        return False

    elif command == "done":
        try:
            n = int(arg)
            if session.toggle_task(n):
                store.save(session)
                show_tasks(session)
            else:
                console.print("[red]잘못된 번호입니다.[/red]")
        except ValueError:
            console.print("[red]번호를 입력해주세요. (예: done 0)[/red]")
        return False

    elif command == "save":
        store.save(session)
        console.print("[green]세션이 저장되었습니다.[/green]")
        return False

    elif command == "list":
        sessions = store.list_sessions()
        if sessions:
            console.print("[bold]저장된 세션:[/bold]")
            for i, name in enumerate(sessions):
                console.print(f"  [{i}] {name}")
        else:
            console.print("[dim]저장된 세션이 없습니다.[/dim]")
        return False

    elif command == "load":
        if arg:
            loaded = store.load(arg)
            if loaded:
                # 새 세션으로 교체 - caller에서 처리 필요
                console.print(f"[green]'{arg}' 세션을 로드했습니다.[/green]")
                return "loaded", loaded
            else:
                console.print(f"[red]'{arg}' 세션을 찾을 수 없습니다.[/red]")
        else:
            console.print("[red]세션 이름을 입력해주세요. (예: load my-task)[/red]")
        return False

    elif command == "guide":
        show_guide(session)
        return False

    elif command == "export":
        show_export(session)
        return False

    else:
        console.print(f"[red]알 수 없는 명령어: {command}[/red]")
        console.print("[dim]'help'를 입력하면 사용 가능한 명령어를 볼 수 있습니다.[/dim]")
        return False


def main():
    # 'auto' 서브커맨드 처리
    if len(sys.argv) > 1 and sys.argv[1] == "auto":
        run_auto_mode(sys.argv[2:])
        return

    store = SessionStore()

    show_banner()

    # 기존 세션 확인
    sessions = store.list_sessions()
    session = None

    if sessions:
        console.print("[bold]저장된 세션이 있습니다:[/bold]")
        for i, name in enumerate(sessions):
            console.print(f"  [{i}] {name}")
        console.print("  [N] 새 세션 시작")
        console.print()

        choice = console.input("[bold cyan]선택 > [/bold cyan]").strip()

        if choice.upper() != "N":
            try:
                idx = int(choice)
                if 0 <= idx < len(sessions):
                    session = store.load(sessions[idx])
                    console.print(f"[green]'{sessions[idx]}' 세션을 로드했습니다.[/green]")
            except ValueError:
                # 이름으로 로드 시도
                loaded = store.load(choice)
                if loaded:
                    session = loaded

    if session is None:
        task_name = prompt_task_name()
        session = Session(task_name=task_name)
        store.save(session)

    # 메인 루프
    show_dashboard(session)

    while True:
        try:
            console.print()
            phase_name = session.current_phase.value.upper()
            cmd = console.input(f"[bold cyan][{phase_name}] > [/bold cyan]").strip()

            if not cmd:
                continue

            result = handle_command(cmd, session, store)

            # load 명령어 처리
            if isinstance(result, tuple) and result[0] == "loaded":
                session = result[1]
                show_dashboard(session)
            elif result is True:
                show_dashboard(session)

        except KeyboardInterrupt:
            console.print()
            store.save(session)
            console.print("[dim]세션이 저장되었습니다. Ctrl+C로 종료합니다.[/dim]")
            sys.exit(0)
        except EOFError:
            store.save(session)
            sys.exit(0)


if __name__ == "__main__":
    main()
