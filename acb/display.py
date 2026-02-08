"""Rich 기반 터미널 UI 출력"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns
from rich.markdown import Markdown

from acb.process import Phase, PHASE_INFO, PHASE_ORDER, Session

console = Console()

PHASE_COLORS = {
    Phase.ANALYZE: "bright_cyan",
    Phase.EXPLORE: "bright_yellow",
    Phase.PLAN: "bright_magenta",
    Phase.IMPLEMENT: "bright_green",
    Phase.VERIFY: "bright_blue",
    Phase.DELIVER: "bright_red",
}

PHASE_ICONS = {
    Phase.ANALYZE: "[1]",
    Phase.EXPLORE: "[2]",
    Phase.PLAN: "[3]",
    Phase.IMPLEMENT: "[4]",
    Phase.VERIFY: "[5]",
    Phase.DELIVER: "[6]",
}


def show_banner():
    banner = Text()
    banner.append("  Agentic Coding Bot  ", style="bold white on blue")
    banner.append("\n  에이전틱 코딩 프로세스 어시스턴트  ", style="dim")
    console.print(Panel(banner, border_style="blue"))


def show_phase_progress(session: Session):
    """현재 프로세스 진행 상황을 표시"""
    progress = session.get_progress()

    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column(width=3)
    table.add_column(width=22)
    table.add_column(width=8)

    for phase in PHASE_ORDER:
        info = PHASE_INFO[phase]
        p = progress[phase.value]
        color = PHASE_COLORS[phase]
        icon = PHASE_ICONS[phase]

        is_current = phase == session.current_phase

        if is_current:
            marker = ">>>"
            style = f"bold {color}"
        elif p["complete"]:
            marker = " + "
            style = f"dim {color}"
        else:
            marker = "   "
            style = f"dim"

        progress_text = f"{p['checked']}/{p['total']}"
        table.add_row(
            Text(marker, style=style),
            Text(f"{icon} {info['title']}", style=style),
            Text(progress_text, style=style),
        )

    console.print(Panel(table, title="Process Progress", border_style="blue"))


def show_current_phase(session: Session):
    """현재 단계 상세 정보 표시"""
    phase = session.current_phase
    info = PHASE_INFO[phase]
    color = PHASE_COLORS[phase]

    # 단계 헤더
    header = Text()
    header.append(f"\n{info['title']}\n", style=f"bold {color}")
    header.append(f'"{info["question"]}"\n\n', style="italic")
    header.append(info["description"], style="dim")

    console.print(Panel(header, border_style=color))


def show_checklist(session: Session, phase: Phase = None):
    """체크리스트 표시"""
    if phase is None:
        phase = session.current_phase

    info = PHASE_INFO[phase]
    items = session.checklists.get(phase.value, [])
    color = PHASE_COLORS[phase]

    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column(width=4, justify="right")
    table.add_column(width=3)
    table.add_column()

    for i, item in enumerate(items):
        idx = Text(f"[{i}]", style="dim")
        check = Text("[x]" if item["checked"] else "[ ]",
                      style="green" if item["checked"] else "dim")
        text = Text(item["text"],
                    style="strike dim" if item["checked"] else "")
        table.add_row(idx, check, text)

    console.print(Panel(table, title=f"Checklist - {info['title']}", border_style=color))


def show_notes(session: Session, phase: str = None):
    """메모 표시"""
    notes = session.notes
    if phase:
        notes = [n for n in notes if n["phase"] == phase]

    if not notes:
        console.print("[dim]기록된 메모가 없습니다.[/dim]")
        return

    for note in notes:
        ph = note["phase"].upper()
        ts = note["timestamp"][:16].replace("T", " ")
        console.print(f"  [dim]{ts}[/dim] [bold cyan][{ph}][/bold cyan] {note['content']}")


def show_tasks(session: Session):
    """작업 목록 표시"""
    if not session.tasks:
        console.print("[dim]등록된 작업이 없습니다.[/dim]")
        return

    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column(width=4, justify="right")
    table.add_column(width=3)
    table.add_column()
    table.add_column(width=10)

    for i, task in enumerate(session.tasks):
        idx = Text(f"[{i}]", style="dim")
        check = Text("[x]" if task["done"] else "[ ]",
                      style="green" if task["done"] else "dim")
        desc = Text(task["description"],
                    style="strike dim" if task["done"] else "")
        ph = Text(task["phase"].upper(), style="dim")
        table.add_row(idx, check, desc, ph)

    done = sum(1 for t in session.tasks if t["done"])
    total = len(session.tasks)
    console.print(Panel(table, title=f"Tasks ({done}/{total})", border_style="green"))


def show_help():
    """도움말 표시"""
    help_text = """
[bold]Navigation[/bold]
  [cyan]next[/cyan]           다음 단계로 이동
  [cyan]prev[/cyan]           이전 단계로 이동
  [cyan]goto <N>[/cyan]       N번 단계로 이동 (1-6)
  [cyan]status[/cyan]         전체 진행 상황 보기

[bold]Checklist[/bold]
  [cyan]check <N>[/cyan]      체크리스트 N번 항목 토글
  [cyan]checklist[/cyan]      현재 단계 체크리스트 보기

[bold]Notes[/bold]
  [cyan]note <text>[/cyan]    메모 추가
  [cyan]notes[/cyan]          모든 메모 보기

[bold]Tasks[/bold]
  [cyan]task <text>[/cyan]    작업 추가
  [cyan]tasks[/cyan]          작업 목록 보기
  [cyan]done <N>[/cyan]       작업 N번 완료/취소 토글

[bold]Session[/bold]
  [cyan]save[/cyan]           세션 저장
  [cyan]list[/cyan]           저장된 세션 목록
  [cyan]load <name>[/cyan]    세션 로드
  [cyan]export[/cyan]         세션 내용을 마크다운으로 출력
  [cyan]guide[/cyan]          현재 단계 가이드 표시

[bold]Other[/bold]
  [cyan]help[/cyan]           도움말 표시
  [cyan]quit[/cyan]           종료
"""
    console.print(Panel(help_text, title="Commands", border_style="blue"))


def show_guide(session: Session):
    """현재 단계에 대한 상세 가이드"""
    phase = session.current_phase
    info = PHASE_INFO[phase]
    color = PHASE_COLORS[phase]

    console.print()
    console.print(f"[bold {color}]=== {info['title']} 가이드 ===[/bold {color}]")
    console.print()
    console.print(f'[italic]핵심 질문: "{info["question"]}"[/italic]')
    console.print()
    console.print(f"[bold]목표:[/bold] {info['description']}")
    console.print()

    console.print("[bold]체크리스트:[/bold]")
    for item in info["checklist"]:
        console.print(f"  - {item}")
    console.print()

    console.print("[bold]산출물:[/bold]")
    for output in info["outputs"]:
        console.print(f"  - {output}")
    console.print()

    if phase == Phase.IMPLEMENT:
        console.print("[bold]구현 원칙:[/bold]")
        console.print("  1. 점진적 구현: 작은 단위로 나누어 구현")
        console.print("  2. 빈번한 검증: 작성 -> 실행 -> 확인 반복")
        console.print("  3. 최소 변경: 요청된 것만 구현")
        console.print("  4. 기존 패턴 존중: 새 패턴보다 기존 컨벤션 우선")


def show_export(session: Session):
    """세션을 마크다운 형식으로 출력"""
    lines = []
    lines.append(f"# {session.task_name}")
    lines.append(f"")
    lines.append(f"- Created: {session.created_at[:16]}")
    lines.append(f"- Updated: {session.updated_at[:16]}")
    lines.append(f"- Current Phase: {session.current_phase.value.upper()}")
    lines.append("")

    progress = session.get_progress()
    for phase in PHASE_ORDER:
        info = PHASE_INFO[phase]
        p = progress[phase.value]
        status = "Complete" if p["complete"] else f"{p['checked']}/{p['total']}"
        lines.append(f"## {info['title']} ({status})")
        lines.append("")

        items = session.checklists.get(phase.value, [])
        for item in items:
            mark = "x" if item["checked"] else " "
            lines.append(f"- [{mark}] {item['text']}")
        lines.append("")

        phase_notes = [n for n in session.notes if n["phase"] == phase.value]
        if phase_notes:
            lines.append("### Notes")
            for n in phase_notes:
                lines.append(f"- {n['content']}")
            lines.append("")

    if session.tasks:
        lines.append("## Tasks")
        for t in session.tasks:
            mark = "x" if t["done"] else " "
            lines.append(f"- [{mark}] [{t['phase'].upper()}] {t['description']}")
        lines.append("")

    console.print(Markdown("\n".join(lines)))
