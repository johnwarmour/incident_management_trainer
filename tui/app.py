"""
Textual TUI for the ITIL Incident Simulation Training Environment.

Uses the same backend Python modules directly (no HTTP required).
Run with: python -m tui.app
"""

from __future__ import annotations

import sys
import os

# Ensure the project root is on the path when run as a script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.widgets import (
    Footer,
    Header,
    Input,
    Label,
    Log,
    ProgressBar,
    RichLog,
    Static,
)
from textual.reactive import reactive

from backend.core import (
    ClaudeClient,
    add_message,
    advance_checkpoint,
    build_checkpoint_score,
    build_debrief,
    detect_checkpoint_complete_signal,
    extract_ticket_updates_from_text,
    get_checkpoint_conversation,
    get_template,
    pick_scenario_type,
)
from backend.models.schemas import (
    CHECKPOINT_ORDER,
    Checkpoint,
    Role,
    SessionState,
)


PRIORITY_COLOR = {"P1": "red", "P2": "dark_orange", "P3": "yellow", "P4": "green"}
CHECKPOINT_LABELS = {
    Checkpoint.DETECTION: "Detection",
    Checkpoint.TRIAGE: "Triage",
    Checkpoint.ESCALATION: "Escalation",
    Checkpoint.COMMUNICATION: "Communication",
    Checkpoint.RESOLUTION: "Resolution",
    Checkpoint.CLOSURE: "Closure",
}


class IncidentTicketWidget(Static):
    """Left panel: live ITIL incident ticket."""

    DEFAULT_CSS = """
    IncidentTicketWidget {
        width: 28;
        border: solid $primary-darken-2;
        padding: 1;
        overflow-y: auto;
    }
    """

    def __init__(self, state: SessionState) -> None:
        super().__init__()
        self._state = state

    def render(self) -> str:
        t = self._state.ticket
        lines = [
            "[bold yellow]INCIDENT RECORD[/bold yellow]",
            f"[bold cyan]{t.inc_number}[/bold cyan]",
            "",
        ]

        if t.title:
            lines.append(f"[bold]{t.title}[/bold]")
        else:
            lines.append("[dim]No title yet[/dim]")

        lines.append("")

        if t.priority:
            color = PRIORITY_COLOR.get(t.priority, "white")
            lines.append(f"Priority: [{color}]{t.priority}[/{color}]")
        if t.impact:
            lines.append(f"Impact:   {t.impact}")
        if t.urgency:
            lines.append(f"Urgency:  {t.urgency}")
        if t.status:
            lines.append(f"Status:   {t.status}")

        if t.affected_systems:
            lines.append("")
            lines.append("[dim]Affected systems:[/dim]")
            for s in t.affected_systems:
                lines.append(f"  • {s}")

        if t.escalation_contacts:
            lines.append("")
            lines.append("[dim]Escalated to:[/dim]")
            for c in t.escalation_contacts:
                lines.append(f"  • [cyan]{c}[/cyan]")

        if t.workaround:
            lines.append("")
            lines.append("[dim]Workaround:[/dim]")
            lines.append(f"  [green]{t.workaround}[/green]")

        lines.append("")
        lines.append("[dim]─── Checkpoints ───[/dim]")
        for cp in CHECKPOINT_ORDER:
            done = cp in self._state.completed_checkpoints
            active = self._state.current_checkpoint == cp
            icon = "[green]✓[/green]" if done else ("[yellow]►[/yellow]" if active else " ")
            label = CHECKPOINT_LABELS[cp]
            color = "green" if done else ("yellow bold" if active else "dim")
            lines.append(f"{icon} [{color}]{label}[/{color}]")

        return "\n".join(lines)

    def refresh_state(self, state: SessionState) -> None:
        self._state = state
        self.refresh()


class CheckpointWidget(Static):
    """Right panel: current checkpoint info and score."""

    DEFAULT_CSS = """
    CheckpointWidget {
        width: 28;
        border: solid $primary-darken-2;
        padding: 1;
        overflow-y: auto;
    }
    """

    GOALS = {
        Checkpoint.DETECTION: ["Acknowledge alert", "Log incident title", "Write description", "List affected systems"],
        Checkpoint.TRIAGE: ["Assess impact", "Assess urgency", "Set priority", "Estimate affected users"],
        Checkpoint.ESCALATION: ["Decide to escalate?", "Contact right people", "Provide context"],
        Checkpoint.COMMUNICATION: ["Notify stakeholders", "Send clear update", "Set update cadence"],
        Checkpoint.RESOLUTION: ["Investigate root cause", "Find workaround/fix", "Verify fix", "Update record"],
        Checkpoint.CLOSURE: ["Close incident", "PIR if P1/P2", "Problem record?", "Lessons learned"],
    }

    def __init__(self, state: SessionState) -> None:
        super().__init__()
        self._state = state
        self._last_score: dict | None = None

    def render(self) -> str:
        cp = self._state.current_checkpoint
        lines = [
            "[bold yellow]CURRENT STEP[/bold yellow]",
            f"[bold]{CHECKPOINT_LABELS[cp].upper()}[/bold]",
            "",
            "[dim]Required actions:[/dim]",
        ]

        goals = self.GOALS.get(cp, [])
        for goal in goals:
            lines.append(f"  □ {goal}")

        lines += [
            "",
            "[dim]Priority matrix:[/dim]",
            "  H×H=P1  H×M=P2  H×L=P3",
            "  M×H=P2  M×M=P3  M×L=P4",
            "  L×H=P3  L×M=P4  L×L=P4",
        ]

        if self._last_score:
            score = self._last_score
            color = "green" if score["score"] >= 80 else ("yellow" if score["score"] >= 60 else "red")
            lines += [
                "",
                "[dim]─── Last score ───[/dim]",
                f"  [{color}]{score['score']}/100[/{color}]",
                f"  {score.get('feedback', '')[:100]}",
            ]

        return "\n".join(lines)

    def refresh_state(self, state: SessionState, last_score: dict | None = None) -> None:
        self._state = state
        if last_score is not None:
            self._last_score = last_score
        self.refresh()


class IncidentSimApp(App):
    """ITIL Incident Simulation — Textual TUI."""

    TITLE = "Incident Sim"
    CSS = """
    Screen {
        layout: grid;
        grid-size: 3;
        grid-columns: 28 1fr 28;
    }
    #chat-log {
        border: solid $primary-darken-2;
        padding: 1;
        height: 1fr;
    }
    #input-bar {
        dock: bottom;
        height: 3;
        border: solid $primary-darken-2;
    }
    #center-col {
        height: 100%;
    }
    """

    BINDINGS = [
        Binding("ctrl+s", "skip_checkpoint", "Skip checkpoint"),
        Binding("ctrl+q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._claude = ClaudeClient()
        self._state: SessionState | None = None
        self._loading = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("[dim]Loading...[/dim]", id="ticket-placeholder")
        yield Vertical(
            RichLog(id="chat-log", highlight=True, markup=True),
            Input(placeholder="Type your response (Enter to send)...", id="input-bar"),
            id="center-col",
        )
        yield Static("[dim]Loading...[/dim]", id="checkpoint-placeholder")
        yield Footer()

    async def on_mount(self) -> None:
        await self._start_session()

    async def _start_session(self, scenario_type: str | None = None) -> None:
        self._loading = True
        log = self.query_one("#chat-log", RichLog)
        log.write("[yellow]Generating scenario... please wait[/yellow]")

        try:
            scenario_type = pick_scenario_type(scenario_type)
            template = get_template(scenario_type)
            scenario_ctx = self._claude.generate_scenario(scenario_type, template)

            state = SessionState(
                scenario_type=scenario_type,
                scenario_title=scenario_ctx["title"],
                scenario_summary=scenario_ctx["summary"],
                scenario_context=scenario_ctx,
            )
            state.ticket.title = scenario_ctx["title"]
            state.ticket.affected_systems = scenario_ctx.get("affected_systems", [])
            self._state = state

            # Replace placeholder widgets
            self.query_one("#ticket-placeholder").remove()
            self.query_one("#checkpoint-placeholder").remove()

            ticket_widget = IncidentTicketWidget(state)
            checkpoint_widget = CheckpointWidget(state)
            await self.mount(ticket_widget, before="#center-col")
            await self.mount(checkpoint_widget)

            opening_prompt = (
                f"[SIMULATION START]\n"
                f"Alert received: {scenario_ctx.get('alert_text', 'Critical alert triggered.')}\n\n"
                f"Introduce yourself as the monitoring system and present the initial alert."
            )
            assistant_opening = self._claude.chat(state, opening_prompt)
            add_message(state, Role.ASSISTANT, assistant_opening)

            log.clear()
            log.write(f"[bold yellow]═══ {state.scenario_title} ═══[/bold yellow]")
            log.write(f"[dim]{state.scenario_summary}[/dim]")
            log.write("")
            log.write(f"[cyan]SYSTEM:[/cyan] {assistant_opening}")

            self.title = f"Incident Sim — {state.scenario_title}"

        except Exception as exc:
            log.write(f"[red]Error starting session: {exc}[/red]")
        finally:
            self._loading = False

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if self._loading or not self._state or self._state.is_complete:
            return

        message = event.value.strip()
        if not message:
            return

        input_widget = self.query_one("#input-bar", Input)
        input_widget.value = ""

        log = self.query_one("#chat-log", RichLog)
        log.write(f"\n[bold white]YOU:[/bold white] {message}")

        self._loading = True
        add_message(self._state, Role.USER, message)

        updates = extract_ticket_updates_from_text(message)
        if updates:
            from backend.core.session import apply_ticket_updates
            apply_ticket_updates(self._state, updates)

        try:
            assistant_msg = self._claude.chat(self._state, message)
            add_message(self._state, Role.ASSISTANT, assistant_msg)
            log.write(f"\n[cyan]SYSTEM:[/cyan] {assistant_msg}")

            # Refresh ticket widget
            try:
                self.query_one(IncidentTicketWidget).refresh_state(self._state)
            except Exception:
                pass

            if detect_checkpoint_complete_signal(assistant_msg):
                cp_conv = get_checkpoint_conversation(self._state, self._state.current_checkpoint)
                raw_eval = self._claude.evaluate_checkpoint(
                    self._state, self._state.current_checkpoint, cp_conv
                )
                score = build_checkpoint_score(self._state.current_checkpoint, raw_eval)
                session_done = advance_checkpoint(self._state, score)

                log.write(
                    f"\n[bold green]✓ Checkpoint complete! Score: {score.score}/100[/bold green]"
                )
                if score.feedback:
                    log.write(f"[dim]{score.feedback}[/dim]")

                try:
                    self.query_one(CheckpointWidget).refresh_state(
                        self._state, raw_eval
                    )
                except Exception:
                    pass

                if session_done:
                    overall_feedback = self._claude.generate_debrief(self._state)
                    log.write("\n[bold yellow]═══ SESSION COMPLETE ═══[/bold yellow]")
                    log.write(f"\nOverall score: [bold]{sum(s.score for s in self._state.scores) // len(self._state.scores)}/100[/bold]")
                    log.write(f"\n{overall_feedback}")
                    log.write("\n[dim]Press Ctrl+Q to quit or Ctrl+S to start a new session.[/dim]")
                else:
                    next_cp = self._state.current_checkpoint
                    log.write(
                        f"\n[yellow]Moving to: {CHECKPOINT_LABELS[next_cp].upper()}[/yellow]"
                    )

        except Exception as exc:
            log.write(f"\n[red]Error: {exc}[/red]")
        finally:
            self._loading = False

    async def action_skip_checkpoint(self) -> None:
        """Force advance the current checkpoint."""
        if not self._state or self._loading or self._state.is_complete:
            return

        log = self.query_one("#chat-log", RichLog)
        self._loading = True
        try:
            cp_conv = get_checkpoint_conversation(self._state, self._state.current_checkpoint)
            raw_eval = self._claude.evaluate_checkpoint(
                self._state, self._state.current_checkpoint, cp_conv
            )
            score = build_checkpoint_score(self._state.current_checkpoint, raw_eval)
            session_done = advance_checkpoint(self._state, score)

            log.write(f"\n[yellow]Skipped to next checkpoint. Score: {score.score}/100[/yellow]")

            try:
                self.query_one(IncidentTicketWidget).refresh_state(self._state)
                self.query_one(CheckpointWidget).refresh_state(self._state, raw_eval)
            except Exception:
                pass

            if session_done:
                overall_feedback = self._claude.generate_debrief(self._state)
                log.write("\n[bold yellow]═══ SESSION COMPLETE ═══[/bold yellow]")
                log.write(f"\n{overall_feedback}")
        except Exception as exc:
            log.write(f"\n[red]Error: {exc}[/red]")
        finally:
            self._loading = False


def main() -> None:
    app = IncidentSimApp()
    app.run()


if __name__ == "__main__":
    main()
