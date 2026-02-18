"""Textual TUI-based interactive shell for Membria."""

import asyncio
import signal
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, Static, RichLog
from textual.message import Message
from rich.text import Text

from .splash import SplashScreen, ExitSplashScreen
from .commands import CommandHandler
from .executor import AgentExecutor
from .ui import MembriaUI
from .usage_tracker import UsageTracker


# ── Status Bar ────────────────────────────────────────────────────────────────

class StatusBar(Static):
    """Live status bar: mode | decisions | per-agent tokens | graph."""

    _mode: str = "pipeline"
    _decisions_ok: int = 0
    _decisions_pending: int = 0
    _tokens: int = 0
    _graph_ok: bool = True

    def update_state(
        self,
        mode: str,
        decisions_ok: int,
        decisions_pending: int,
        tokens: int,
        graph_ok: bool,
    ) -> None:
        self._mode = mode
        self._decisions_ok = decisions_ok
        self._decisions_pending = decisions_pending
        self._tokens = tokens
        self._graph_ok = graph_ok
        self.refresh()

    def render(self) -> Text:
        graph = (
            "[#A3BE8C]✓ graph[/#A3BE8C]"
            if self._graph_ok
            else "[#BF616A]✗ graph[/#BF616A]"
        )
        tok = f"{self._tokens:,}" if self._tokens else "0"
        return Text.from_markup(
            f" [#81A1C1]{self._mode}[/#81A1C1]"
            f"  [dim]│[/dim]"
            f"  [#A3BE8C]✓{self._decisions_ok}[/#A3BE8C]"
            f" [#EBCB8B]⊙{self._decisions_pending}[/#EBCB8B]"
            f"  [dim]│[/dim]"
            f"  [#EBCB8B]{tok} tok[/#EBCB8B]"
            f"  [dim]│[/dim]"
            f"  {graph}"
        )


# ── Side Panel ────────────────────────────────────────────────────────────────

class SidePanel(Static):
    """Right sidebar: agents, calibration, session cost, last decisions."""

    # Session state — updated by MembriaApp
    session_tokens: int = 0
    session_cost: float = 0.0
    decision_count: int = 0
    _decisions: list

    def __init__(self, config_manager=None, **kwargs):
        super().__init__(**kwargs)
        self._decisions = []
        self._config_manager = config_manager

    def compose(self) -> ComposeResult:
        yield Static("[bold]🤖 AGENTS[/bold]", id="panel-agents-title")
        yield Static("", id="panel-agents")

        yield Static("[bold]📊 CALIBRATION[/bold]", id="panel-cal-title")
        yield Static("", id="panel-cal")

        yield Static("[bold]💬 SESSION[/bold]", id="panel-session-title")
        yield Static("", id="panel-session")

        yield Static("[bold]🔍 LAST DECISIONS[/bold]", id="panel-dec-title")
        yield Static("", id="panel-decisions")

    def on_mount(self) -> None:
        self._refresh_agents()
        self._refresh_calibration()
        self._refresh_session()
        self._refresh_decisions()

    # ── public API ────────────────────────────────────────────────────────────

    def add_decision(self, label: str, confidence: int, success: bool = True) -> None:
        """Prepend a new decision; keep last 5."""
        status = "✓" if success else "✗"
        self._decisions.insert(0, (label, confidence, status))
        self._decisions = self._decisions[:5]
        self.decision_count = len(self._decisions)
        self._refresh_decisions()
        self._refresh_session()

    def update_session(self, tokens: int, decisions: int) -> None:
        self.session_tokens = tokens
        self.decision_count = decisions
        self._refresh_session()

    # ── internal renderers ────────────────────────────────────────────────────

    def _refresh_agents(self) -> None:
        config_manager = self._config_manager
        if config_manager is None:
            app = getattr(self, "app", None)
            config_manager = getattr(app, "config_manager", None) if app else None
        team = None
        if config_manager and getattr(config_manager, "config", None):
            team = getattr(config_manager.config, "team", None)

        if isinstance(team, dict) and "agents" in team and isinstance(team["agents"], dict):
            providers = {}
            if config_manager and getattr(config_manager, "config", None):
                providers = getattr(config_manager.config, "providers", {}) or {}
            lines = []
            for name, agent_data in team["agents"].items():
                role = agent_data.get("role", name)
                label = agent_data.get("label") or role.replace("_", " ").title()
                provider_name = agent_data.get("provider", "")
                provider = providers.get(provider_name, {}) if isinstance(providers, dict) else {}
                provider_enabled = bool(provider.get("enabled", False)) if isinstance(provider, dict) else False
                provider_key = provider.get("api_key", "") if isinstance(provider, dict) else ""
                provider_auth = provider.get("auth_method", "") if isinstance(provider, dict) else ""
                provider_token = provider.get("auth_token", "") if isinstance(provider, dict) else ""
                if not provider_enabled or (not provider_key and not provider_token):
                    model = "not configured"
                else:
                    model = agent_data.get("model") or provider.get("model") or "unknown"
                on_demand = bool(agent_data.get("on_demand", False))
                status = "[#EBCB8B]💤[/#EBCB8B]" if on_demand else "[#A3BE8C]✅[/#A3BE8C]"
                lines.append(f"{status} [bold]{label}[/bold]")
                lines.append(f"   [dim]{model}[/dim]")
            self.query_one("#panel-agents", Static).update("\n".join(lines))
            return

        self.query_one("#panel-agents", Static).update(
            "[#A3BE8C]✅[/#A3BE8C] 🏗️  [bold]Architect[/bold]\n"
            "   [dim]not configured[/dim]\n"
            "[#A3BE8C]✅[/#A3BE8C] ⚡  [bold]Senior Dev[/bold]\n"
            "   [dim]not configured[/dim]\n"
            "[#A3BE8C]✅[/#A3BE8C] 💻  [bold]Junior Dev[/bold]\n"
            "   [dim]not configured[/dim]\n"
            "[#A3BE8C]✅[/#A3BE8C] 🔍  [bold]Reviewer[/bold]\n"
            "   [dim]not configured[/dim]\n"
            "[#EBCB8B]💤[/#EBCB8B] 🐛  [dim]Debugger (on demand)[/dim]"
        )

    def _refresh_calibration(self) -> None:
        self.query_one("#panel-cal", Static).update(
            "Architect  [#A3BE8C]89%[/#A3BE8C] [dim](142 dec)[/dim]\n"
            "Security   [#A3BE8C]93%[/#A3BE8C] [dim](87 dec)[/dim]\n"
            "DB Expert  [#A3BE8C]85%[/#A3BE8C] [dim](156 dec)[/dim]\n"
            "[dim]─────────────────────────[/dim]\n"
            "[dim]Overall:[/dim] [#EBCB8B]−8%[/#EBCB8B] [dim]overconfident ↑[/dim]"
        )

    def _refresh_session(self) -> None:
        self.query_one("#panel-session", Static).update(
            f"[dim]Decisions:[/dim] [#88C0D0]{self.decision_count}[/#88C0D0]\n"
            f"[dim]Mode:[/dim]      [#81A1C1]pipeline[/#81A1C1]"
        )

    def _refresh_decisions(self) -> None:
        items = self._decisions or [
            ("Plan DB", 100, "✓"),
            ("API design", 85, "✓"),
            ("Auth flow", 92, "✓"),
        ]
        lines = []
        for i, (label, conf, status) in enumerate(items, 1):
            color = "#A3BE8C" if status == "✓" else "#BF616A"
            lines.append(
                f"[dim]{i}.[/dim] {label} [{color}]({conf}%) {status}[/{color}]"
            )
        self.query_one("#panel-decisions", Static).update("\n".join(lines))


# ── Input Container ───────────────────────────────────────────────────────────

class InputContainer(Vertical):
    """Input row with prompt label + text field + command history."""

    class UserSubmit(Message):
        def __init__(self, text: str) -> None:
            super().__init__()
            self.text = text

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._history: list[str] = []
        self._hist_idx: int = -1

    def compose(self) -> ComposeResult:
        with Horizontal(id="inp-row"):
            yield Static("[bold #88C0D0]membria ▸[/bold #88C0D0]", id="inp-prompt")
            yield Input(id="inp", placeholder="Type a task or /help")

    def on_mount(self) -> None:
        self.query_one("#inp", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if text:
            self._history.append(text)
            self._hist_idx = -1
            self.post_message(self.UserSubmit(text))
        event.input.value = ""

    def on_key(self, event) -> None:
        if event.key == "up" and self._history:
            if self._hist_idx == -1:
                self._hist_idx = len(self._history) - 1
            elif self._hist_idx > 0:
                self._hist_idx -= 1
            self.query_one("#inp", Input).value = self._history[self._hist_idx]
            event.prevent_default()
        elif event.key == "down" and self._history:
            if self._hist_idx >= 0:
                self._hist_idx += 1
                inp = self.query_one("#inp", Input)
                if self._hist_idx >= len(self._history):
                    self._hist_idx = -1
                    inp.value = ""
                else:
                    inp.value = self._history[self._hist_idx]
            event.prevent_default()


# ── Main App ──────────────────────────────────────────────────────────────────

class MembriaApp(App):
    """Membria CLI — Decision Intelligence SuperAgent."""

    TITLE = "Membria CLI"
    SUB_TITLE = "Decision Intelligence SuperAgent"

    BINDINGS = [
        Binding("ctrl+d", "quit", "Quit"),
        Binding("ctrl+l", "clear_output", "Clear"),
        Binding("ctrl+m", "toggle_mouse", "Mouse"),
    ]

    CSS = """
    /* ── App root ── */
    App {
        background: $background;
    }

    /* ── ANSI fallback (override terminal bg) ── */
    Screen:ansi {
        background: $background;
        color: $foreground;
    }

    /* ── Screen ── */
    Screen {
        layout: vertical;
        background: $background;
    }

    /* ── Header ── */
    Header {
        dock: top;
        height: 1;
        background: $background;
        border-bottom: solid $primary 60%;
        color: $primary;
        text-style: bold;
    }

    /* ── Main area (output + sidebar) ── */
    #main {
        height: 1fr;
        layout: horizontal;
        background: $background;
    }

    #output {
        width: 1fr;
        height: 1fr;
        background: $background;
        border-right: solid $primary 30%;
        scrollbar-color: $primary;
        scrollbar-color-hover: $secondary;
        padding: 0 1;
    }

    /* ── Sidebar ── */
    #sidebar {
        width: 34;
        height: 1fr;
        background: $panel;
        padding: 0 1 1 1;
        layout: vertical;
        overflow-y: auto;
        scrollbar-color: $primary;
    }

    #panel-agents-title,
    #panel-cal-title,
    #panel-session-title,
    #panel-dec-title {
        height: 1;
        margin-top: 1;
        color: $primary;
        text-style: bold;
    }

    #panel-agents,
    #panel-cal,
    #panel-session,
    #panel-decisions {
        height: auto;
        padding: 0 0 1 1;
        border-bottom: solid $primary 25%;
    }

    /* ── Input row ── */
    #input-container {
        height: 3;
        background: $panel;
        border-top: solid $primary 50%;
        border-bottom: solid $primary 50%;
        padding: 0;
    }

    #inp-row {
        height: 3;
        padding: 0 1;
    }

    #inp-prompt {
        width: auto;
        height: 1;
        margin-top: 1;
        color: $primary;
    }

    #inp {
        width: 1fr;
        height: 1;
        background: $surface;
        border: none;
        padding: 0 1;
    }

    #inp:focus {
        border: none;
    }

    /* ── Status bar ── */
    #status-bar {
        height: 3;
        background: $background;
        border-top: solid $primary 30%;
        border-bottom: solid $primary 30%;
        padding: 0 1;
        color: $foreground;
        content-align: left middle;
    }

    /* ── Footer ── */
    Footer {
        dock: bottom;
        background: $panel;
        border-top: solid $primary 40%;
        height: 1;
        color: $primary;
    }

    Footer > .footer--key {
        background: $background;
        color: $primary;
        text-style: bold;
    }
    """

    def __init__(self, config_manager):
        # Set theme before super().__init__() so Stylesheet is created with Nord vars
        object.__setattr__(self, "_reactive_theme", "nord")
        super().__init__(ansi_color=False)
        self.config_manager = config_manager
        self.executor = AgentExecutor(config_manager)
        self.ui = MembriaUI()
        self.executor.set_ui(self.ui)
        self.command_handler = CommandHandler(self)
        self.usage_tracker = UsageTracker()
        self.skip_splash = False

    def get_css_variables(self) -> dict[str, str]:
        variables = super().get_css_variables()
        try:
            import os
            term_program = os.environ.get("TERM_PROGRAM", "")
            if term_program == "Apple_Terminal":
                variables["background"] = "#303030"
                variables["surface"] = "#3A3A3A"
                variables["panel"] = "#444444"
        except Exception:
            pass
        return variables

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Horizontal(id="main"):
            self.output = RichLog(id="output", markup=True, highlight=True)
            yield self.output
            yield SidePanel(id="sidebar", config_manager=self.config_manager)

        yield InputContainer(id="input-container")

        self.status_bar = StatusBar(id="status-bar")
        yield self.status_bar

        # No Footer — it would cover the status bar; keybindings shown in header

    async def on_mount(self) -> None:
        # Force theme watcher to apply classes and refresh CSS.
        self.theme = "nord"
        self._watch_theme("nord")
        try:
            from textual import constants as _textual_constants
            debug = [
                f"theme={self.theme}",
                f"current_theme={self.current_theme.name}",
                f"ansi_color={self.ansi_color}",
                f"color_system={_textual_constants.COLOR_SYSTEM}",
                f"console_color_system={self.console.color_system}",
                f"background={self.current_theme.background}",
                f"surface={self.current_theme.surface}",
                f"panel={self.current_theme.panel}",
            ]
            try:
                screen_bg = self.screen.styles.background
                output_bg = self.query_one("#output").styles.background
                debug.append(f"screen_bg={screen_bg} rgb={getattr(screen_bg, 'rgb', None)} ansi={getattr(screen_bg, 'ansi', None)}")
                debug.append(f"output_bg={output_bg} rgb={getattr(output_bg, 'rgb', None)} ansi={getattr(output_bg, 'ansi', None)}")
            except Exception:
                debug.append("style_inspect_failed")
            Path("/tmp/membria_textual_debug.txt").write_text("\n".join(debug))
        except Exception:
            pass

        try:
            from .context_detector import ContextDetector
            detector = ContextDetector()
            ctx = detector.detect()
            roles = detector.get_expert_roles(ctx)
            self.output.write(
                f"[bold #88C0D0]Membria CLI[/bold #88C0D0]  "
                f"[dim]{ctx.value} · {', '.join(roles)}[/dim]"
            )
            self.output.write("")
        except Exception:
            self.output.write("[bold #88C0D0]Membria CLI — Decision Intelligence SuperAgent[/bold #88C0D0]")
            self.output.write("")

        if not self.skip_splash:
            try:
                self.push_screen(SplashScreen())
            except Exception:
                pass

        if self.config_manager.is_first_run():
            try:
                from .onboarding_screens import OnboardingFlow
                flow = OnboardingFlow(self, self.config_manager)
                flow.start()
                while len(self.screen_stack) > 1:
                    await asyncio.sleep(0.1)
            except Exception:
                pass

    async def on_input_container_user_submit(self, msg: InputContainer.UserSubmit) -> None:
        text = msg.text
        self.output.write(f"[bold #88C0D0]▸[/bold #88C0D0] [bold]{text}[/bold]")

        try:
            if text.startswith("/"):
                result = await self.command_handler.handle_command(text)
                if result:
                    self.output.write(result)
            else:
                result = await self.executor.run_orchestration(text)
                if result:
                    self.output.write(str(result))
        except Exception as e:
            self.output.write(f"[#BF616A]✗ Error:[/#BF616A] {e}")

        # Sync sidebar + status bar
        try:
            panel = self.query_one("#sidebar", SidePanel)
            total_tok = sum(u.tokens_used for u in self.usage_tracker.usage.values())
            panel.update_session(total_tok, panel.decision_count)

            mode = self.config_manager.config.get("orchestration", {}).get("mode", "pipeline")
            self.status_bar.update_state(
                mode=mode,
                decisions_ok=panel.decision_count,
                decisions_pending=0,
                tokens=total_tok,
                graph_ok=True,
            )
        except Exception:
            pass

    def action_clear_output(self) -> None:
        self.query_one("#output", RichLog).clear()

    def action_toggle_mouse(self) -> None:
        driver = getattr(self, "_driver", None)
        if not driver:
            return
        if getattr(driver, "_mouse", True):
            driver._mouse = False
            if hasattr(driver, "_disable_mouse_support"):
                driver._disable_mouse_support()
            try:
                self.output.write("[dim]Mouse disabled (terminal selection enabled). Ctrl+M to re-enable.[/dim]")
            except Exception:
                pass
        else:
            driver._mouse = True
            if hasattr(driver, "_enable_mouse_support"):
                driver._enable_mouse_support()
            try:
                self.output.write("[dim]Mouse enabled (UI click). Ctrl+M to disable for selection.[/dim]")
            except Exception:
                pass

def run_textual_shell(config_manager, skip_splash: bool = False):
    """Launch Membria TUI."""
    app = MembriaApp(config_manager)
    app.skip_splash = skip_splash

    def sig_handler(signum, frame):
        app.exit()

    original = signal.signal(signal.SIGINT, sig_handler)
    try:
        app.run()
    finally:
        signal.signal(signal.SIGINT, original)
