"""Textual TUI-based interactive shell for Membria."""

import asyncio
import json
import time
import re
import os
import shlex
import subprocess
import signal
from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Footer, Header, Input, Static, RichLog, Button, Select
from textual.screen import Screen
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
    """Right sidebar: workspace, roles, MCP, and recent decisions."""

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
        yield Static("[bold]📁 WORKSPACE[/bold]", id="panel-workspace-title")
        yield Static("", id="panel-workspace")

        yield Static("─" * 30, classes="panel-divider")
        yield Static("[bold]🧩 ROLES[/bold]", id="panel-roles-title")
        yield Static("", id="panel-roles")
        yield Static("─" * 30, classes="panel-divider")

        yield Static("[bold]🧠 SKILLS[/bold]", id="panel-skills-title")
        yield Static("", id="panel-skills")
        yield Static("─" * 30, classes="panel-divider")

        yield Static("[bold]💬 SESSION[/bold]", id="panel-session-title")
        yield Static("", id="panel-session")
        yield Static("─" * 30, classes="panel-divider")

        yield Static("[bold]🔍 LAST DECISIONS[/bold]", id="panel-dec-title")
        yield Static("", id="panel-decisions")

    def on_mount(self) -> None:
        self._refresh_workspace()
        self._refresh_roles()
        self._refresh_decisions()
        self._refresh_session_local()
        self._refresh_skills()  # launches background thread, returns immediately

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

    def _refresh_workspace(self) -> None:
        config_manager = self._config_manager
        if config_manager is None:
            app = getattr(self, "app", None)
            config_manager = getattr(app, "config_manager", None) if app else None
        cfg = getattr(config_manager, "config", None) if config_manager else None
        project_id = getattr(cfg, "project_id", "default") if cfg else "default"
        team_id = getattr(cfg, "team_id", "default") if cfg else "default"

        # Use active workspace from app state — no filesystem scan
        ws_id = ""
        try:
            app = getattr(self, "app", None)
            ws_id = getattr(app, "_active_ws_id", "") or ""
        except Exception:
            pass

        self.query_one("#panel-workspace", Static).update(
            f"[dim]Project:[/dim] [#88C0D0]{(ws_id or project_id)}[/#88C0D0]\n"
            f"[dim]Team:[/dim]    [#88C0D0]{team_id}[/#88C0D0]"
        )

    def _refresh_roles(self) -> None:
        try:
            roles = self._get_active_roles()
            lines = [f"[#A3BE8C]✅[/#A3BE8C] {r}" for r in roles]
            self.query_one("#panel-roles", Static).update("\n".join(lines))
        except Exception:
            self.query_one("#panel-roles", Static).update("[dim]No roles detected[/dim]")

    def _refresh_skills(self) -> None:
        """Fetch skills in background thread, update UI safely via call_from_thread."""
        import threading

        def _fetch():
            try:
                from membria.graph import GraphClient
                graph = GraphClient()
                graph.connect()
                roles = self._get_active_roles()
                lines = []
                for role in roles:
                    links = graph.get_role_links(role) if graph.connected else {"skills": []}
                    skills = links.get("skills") or []
                    if not skills:
                        lines.append(f"[dim]{role}:[/dim] [dim]—[/dim]")
                        continue
                    skill_labels = []
                    for sk in skills[:3]:
                        name = sk.get("name") if isinstance(sk, dict) else str(sk)
                        skill_labels.append(name)
                    more = f" +{len(skills)-3}" if len(skills) > 3 else ""
                    lines.append(f"[dim]{role}:[/dim] " + ", ".join(skill_labels) + more)
                text = "\n".join(lines) if lines else "[dim]Skills unavailable[/dim]"
            except Exception:
                text = "[dim]Skills unavailable[/dim]"

            def _update():
                try:
                    self.query_one("#panel-skills", Static).update(text)
                except Exception:
                    pass
            try:
                self.app.call_from_thread(_update)
            except Exception:
                pass

        threading.Thread(target=_fetch, daemon=True).start()

    def _get_active_roles(self) -> list:
        cfg = None
        if self._config_manager and getattr(self._config_manager, "config", None):
            cfg = self._config_manager.config
        agi_cfg = getattr(cfg, "agi", {}) if cfg else {}
        research_cfg = getattr(cfg, "research", {}) if cfg else {}
        if agi_cfg and agi_cfg.get("research_mode"):
            roles = research_cfg.get("roles") or ["planner", "synth", "red_team", "final"]
            return [r for r in roles if r]
        # Cache result — filesystem scan is expensive, roles don't change often
        if not hasattr(self, "_cached_roles"):
            from .context_detector import ContextDetector
            detector = ContextDetector()
            ctx = detector.detect()
            self._cached_roles = detector.get_expert_roles(ctx) or ["architect", "implementer", "reviewer", "security_auditor"]
        return self._cached_roles

    def _refresh_session_local(self) -> None:
        """Fast session refresh — only checks local process status, no HTTP."""
        try:
            from membria.process_manager import ProcessManager
            cfg = None
            if self._config_manager and getattr(self._config_manager, "config", None):
                cfg = self._config_manager.config
            manager = ProcessManager()
            daemon_cfg = getattr(cfg, "daemon", None) if cfg else None
            port = 3117
            if isinstance(daemon_cfg, dict):
                port = int(daemon_cfg.get("port", 3117))
            else:
                port = int(getattr(daemon_cfg, "port", 3117))
            running = manager.is_running()
            icon = "[#A3BE8C]✅[/#A3BE8C]" if running else "[#BF616A]✗[/#BF616A]"
            mcp_line = f"[dim]MCP:[/dim]       {icon} [dim]{port}[/dim]"
            decision_line = (
                f"[dim]Decisions:[/dim] [#88C0D0]{self.decision_count}[/#88C0D0] [dim](this session)[/dim]"
                if self.decision_count > 0
                else "[dim]Decisions:[/dim] [dim]No decisions yet[/dim]"
            )
            self.query_one("#panel-session", Static).update(f"{decision_line}")
        except Exception:
            pass

    def _refresh_session(self) -> None:
        mcp_line = ""
        providers_line = ""
        try:
            from membria.process_manager import ProcessManager
            cfg = None
            if self._config_manager and getattr(self._config_manager, "config", None):
                cfg = self._config_manager.config
            manager = ProcessManager()
            # Auto-start daemon if enabled and not running (throttle attempts)
            daemon_cfg = getattr(cfg, "daemon", None) if cfg else None
            auto_start = False
            port = 3117
            if isinstance(daemon_cfg, dict):
                auto_start = bool(daemon_cfg.get("auto_start", False))
                port = int(daemon_cfg.get("port", 3117))
            else:
                auto_start = bool(getattr(daemon_cfg, "auto_start", False))
                port = int(getattr(daemon_cfg, "port", 3117))
            if cfg and daemon_cfg and auto_start:
                now = time.time()
                last = getattr(self, "_last_mcp_start_attempt", 0)
                if now - last > 10:
                    setattr(self, "_last_mcp_start_attempt", now)
                    if not manager.is_running():
                        ok, msg = manager.start(port=port)
                        if not ok:
                            setattr(self, "_mcp_last_error", msg)
                            setattr(self, "_mcp_error_reported", False)
            status = manager.status()
            running = status.is_running
            if running:
                icon = "[#A3BE8C]✅[/#A3BE8C]"
                pid_text = ""
                setattr(self, "_mcp_last_error", "")
                setattr(self, "_mcp_error_reported", False)
            else:
                icon = "[#BF616A]✗[/#BF616A]"
                pid_text = ""
                try:
                    if manager.pid_file.exists():
                        pid_text = " [#EBCB8B]stale pid[/#EBCB8B]"
                except Exception:
                    pass
                err = getattr(self, "_mcp_last_error", "")
                if err:
                    pid_text = f"{pid_text} [dim]{err[:40]}[/dim]"
                    # Also emit a one-time message to the output area
                    if not getattr(self, "_mcp_error_reported", False):
                        try:
                            self._append_md(f"[#BF616A]MCP start failed:[/#BF616A] {err}")
                        except Exception:
                            pass
                        setattr(self, "_mcp_error_reported", True)
            mcp_line = f"[dim]MCP:[/dim]       {icon} [dim]{port}[/dim] {pid_text}".rstrip()
        except Exception:
            mcp_line = "[dim]MCP:[/dim]       [#BF616A]✗[/#BF616A]"
        try:
            mcp_front, mcp_front_err = self._get_mcp_front_providers()
            if mcp_front:
                rendered = []
                down = []
                for p in mcp_front:
                    name = p.get("display_name") or p.get("name") or "unknown"
                    ok = p.get("ping_ok")
                    dot = "[#A3BE8C]●[/#A3BE8C]" if ok else "[#BF616A]●[/#BF616A]"
                    msg = p.get("ping_message") or ""
                    extra = f" [dim]({msg})[/dim]" if msg else ""
                    rendered.append(f"{dot} {name}{extra}")
                    if not ok:
                        down.append(name)
                names = ", ".join(rendered)
                down_suffix = f" [dim](down: {', '.join(down)})[/dim]" if down else ""
                providers_line = f"[dim]Providers:[/dim] [#88C0D0]{len(mcp_front)}[/#88C0D0]{down_suffix}"
                providers_details = "\n".join(rendered)
            else:
                if mcp_front_err:
                    short_err = mcp_front_err.replace("\n", " ")[:40]
                    providers_line = (
                        "[dim]Providers:[/dim] [dim]unknown (MCP Front)[/dim] "
                        f"[dim]{short_err}[/dim]"
                    )
                    providers_details = ""
                    if not getattr(self, "_mcp_front_error_reported", False):
                        try:
                            self._append_md(f"[#BF616A]MCP Front unreachable:[/#BF616A] {mcp_front_err}")
                        except Exception:
                            pass
                        setattr(self, "_mcp_front_error_reported", True)
                else:
                    providers_line = "[dim]Providers:[/dim] [dim]unknown (MCP Front)[/dim]"
                    providers_details = ""
        except Exception:
            providers_line = "[dim]Providers:[/dim] [dim]unknown (MCP Front)[/dim]"
            providers_details = ""
        decision_line = (
            f"[dim]Decisions:[/dim] [#88C0D0]{self.decision_count}[/#88C0D0] [dim](this session)[/dim]"
            if self.decision_count > 0
            else "[dim]Decisions:[/dim] [dim]No decisions yet[/dim]"
        )
        self.query_one("#panel-session", Static).update(
            f"{decision_line}"
        )

    def _refresh_decisions(self) -> None:
        items = self._decisions
        if not items:
            self.query_one("#panel-decisions", Static).update("[dim]No decisions yet[/dim]")
            return
        lines = []
        for i, (label, conf, status) in enumerate(items, 1):
            color = "#A3BE8C" if status == "✓" else "#BF616A"
            lines.append(
                f"[dim]{i}.[/dim] {label} [{color}]({conf}%) {status}[/{color}]"
            )
        self.query_one("#panel-decisions", Static).update("\n".join(lines))

    def _mcp_front_base(self) -> str:
        base = os.getenv("MEMBRIA_MCP_FRONT_URL", "").strip()
        if not base:
            try:
                cfg = self._config_manager.config if self._config_manager else None
                mcp_front = getattr(cfg, "mcp_front", None) if cfg else None
                base = (getattr(mcp_front, "base_url", "") or "").strip()
            except Exception:
                base = ""
        if not base:
            base = "http://127.0.0.1:8080"
        return base.rstrip("/")

    def _get_mcp_front_providers(self) -> tuple[list[dict], str]:
        try:
            app = getattr(self, "app", None)
            if app and hasattr(app, "_ensure_mcp_front_started"):
                app._ensure_mcp_front_started(force=False)
        except Exception:
            pass
        now = time.time()
        last = getattr(self, "_mcp_front_last_fetch", 0.0)
        cache = getattr(self, "_mcp_front_cache", None)
        if cache is not None and (now - last) < 30:
            return cache, getattr(self, "_mcp_front_last_error", "")

        # Non-blocking fetch to avoid freezing input
        inflight = getattr(self, "_mcp_front_fetch_inflight", False)
        if inflight:
            return cache or [], getattr(self, "_mcp_front_last_error", "fetching")

        def _fetch():
            try:
                import urllib.request
                import urllib.parse
                base = self._mcp_front_base()
                urls = [f"{base}/api/providers"]
                try:
                    parsed = urllib.parse.urlparse(base)
                    if parsed.hostname == "localhost":
                        alt = parsed._replace(netloc=f"127.0.0.1:{parsed.port or 8080}").geturl().rstrip("/")
                        if alt != base:
                            urls.append(f"{alt}/api/providers")
                    if parsed.hostname == "127.0.0.1":
                        alt = parsed._replace(netloc=f"localhost:{parsed.port or 8080}").geturl().rstrip("/")
                        if alt != base:
                            urls.append(f"{alt}/api/providers")
                except Exception:
                    pass

                html = ""
                last_err = ""
                for url in urls:
                    try:
                        with urllib.request.urlopen(url, timeout=1.0) as resp:
                            html = resp.read().decode("utf-8", "ignore")
                            last_err = ""
                            break
                    except Exception as e:
                        last_err = str(e)
                        continue
                if not html:
                    raise RuntimeError(last_err or "MCP Front not reachable")
                providers = []
                try:
                    payload = json.loads(html)
                    if isinstance(payload, dict):
                        providers = payload.get("providers") or []
                except Exception:
                    providers = []
                setattr(self, "_mcp_front_cache", providers)
                setattr(self, "_mcp_front_last_fetch", time.time())
                setattr(self, "_mcp_front_last_error", "")
                setattr(self, "_mcp_front_error_reported", False)
            except Exception as e:
                setattr(self, "_mcp_front_cache", [])
                setattr(self, "_mcp_front_last_fetch", time.time())
                setattr(self, "_mcp_front_last_error", str(e))
            finally:
                setattr(self, "_mcp_front_fetch_inflight", False)

        try:
            import threading
            setattr(self, "_mcp_front_fetch_inflight", True)
            threading.Thread(target=_fetch, daemon=True).start()
        except Exception:
            setattr(self, "_mcp_front_fetch_inflight", False)
        return cache or [], getattr(self, "_mcp_front_last_error", "fetching")

class ProvidersScreen(Screen):
    """Providers + model picker."""

    BINDINGS = [
        Binding("escape", "close", "Close"),
    ]

    def __init__(self, app_ref, **kwargs):
        super().__init__(**kwargs)
        self._app_ref = app_ref

    def compose(self) -> ComposeResult:
        yield Static("[bold]Providers & Models[/bold]", id="providers-title")
        yield VerticalScroll(Static("", id="providers-body"), id="providers-scroll")
        yield Button("Close", id="providers-close")

    def on_mount(self) -> None:
        self.refresh_view()

    def refresh_view(self) -> None:
        body = self.query_one("#providers-body", Static)
        providers = []
        err = ""
        try:
            panel = self._app_ref.query_one("#sidebar", SidePanel)
            # Force refresh (avoid stale cache)
            try:
                setattr(panel, "_mcp_front_cache", None)
                setattr(panel, "_mcp_front_last_fetch", 0.0)
            except Exception:
                pass
            providers, err = panel._get_mcp_front_providers()
        except Exception as e:
            err = str(e)
        if not providers:
            msg = "No providers available"
            if err:
                msg = f"{msg}: {err}"
            body.update(f"[dim]{msg}[/dim]")
            return
        lines = []
        for p in providers:
            name = p.get("display_name") or p.get("name") or "unknown"
            ok = p.get("ping_ok")
            dot = "[#A3BE8C]●[/#A3BE8C]" if ok else "[#BF616A]●[/#BF616A]"
            cfg = "configured" if p.get("configured") else "not configured"
            models = p.get("model_ids") or []
            if len(models) > 20:
                models = models[:20] + ["..."]
            models_line = ", ".join(models) if models else "n/a"
            mf_ok = p.get("model_fetch_ok", False)
            mf_code = p.get("model_fetch_code", 0)
            mf_err = p.get("model_fetch_error", "")
            if not mf_ok and mf_err:
                models_line = f"{models_line} [dim]({mf_err}{' ' + str(mf_code) if mf_code else ''})[/dim]"
            lines.append(f"{dot} {name} [dim]({cfg})[/dim]")
            lines.append(f"[dim]Models:[/dim] {models_line}")
            lines.append("")
        body.update("\n".join(lines).rstrip())

    def action_close(self) -> None:
        self.app.pop_screen()
        try:
            self._app_ref.focus_input()
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "providers-close":
            self.app.pop_screen()
            try:
                self._app_ref.focus_input()
            except Exception:
                pass


class TextWizard:
    """Step-by-step text wizard in the main output."""

    def __init__(self, app_ref):
        self.app = app_ref
        self.step = 0
        self.data = {}
        self.roles = ["architect", "implementer", "reviewer", "security_auditor"]
        self._role_index = 0
        self._provider_models = {}
        self._providers = []
        self._default_provider = "kilo-code"
        self._skills = []
        self._history = []

    def _known_models(self, provider: str) -> list[str]:
        known = {
            "openai": [
                "gpt-5.3-codex",
                "gpt-5.2-codex",
                "gpt-5.1-codex-max",
                "gpt-5.2",
                "gpt-5.1-codex-mini",
            ],
            "anthropic": [
                "claude-opus-4-6",
                "claude-sonnet-4-6",
                "claude-haiku-4-5",
            ],
            "kilo-code": ["kilo/auto"],
        }
        return known.get(provider, [])

    def _load_providers(self) -> None:
        panel = self.app.query_one("#sidebar", SidePanel)
        try:
            setattr(panel, "_mcp_front_cache", None)
            setattr(panel, "_mcp_front_last_fetch", 0.0)
        except Exception:
            pass
        providers, _err = panel._get_mcp_front_providers()
        if not providers:
            providers = [
                {"name": "openai", "display_name": "OpenAI", "model_ids": self._known_models("openai")},
                {"name": "anthropic", "display_name": "Claude", "model_ids": self._known_models("anthropic")},
                {"name": "kilo-code", "display_name": "Kilo Code", "model_ids": self._known_models("kilo-code")},
            ]
        self._providers = providers
        self._provider_models = {p.get("name"): (p.get("model_ids") or []) for p in providers}
        if providers:
            self._default_provider = providers[0].get("name") or "kilo-code"

    def _load_skills(self) -> None:
        try:
            from membria.graph import GraphClient
            graph = GraphClient()
            if graph.connect():
                self._skills = graph.list_skills(limit=200)
            else:
                self._skills = []
        except Exception:
            self._skills = []

    def start(self) -> None:
        self._load_providers()
        self._load_skills()
        self.app._append_md("Chat setup (text)")
        self.app._append_md("[dim]Type a number to choose. 'back' to go back. 'cancel' to exit.[/dim]")
        self._prompt_step()

    def _push_state(self) -> None:
        snap = (self.step, json.loads(json.dumps(self.data)), self._role_index)
        self._history.append(snap)

    def _pop_state(self) -> bool:
        if not self._history:
            return False
        self.step, self.data, self._role_index = self._history.pop()
        return True

    def _prompt_step(self) -> None:
        self.app._append_md("")
        self.app._append_md("─" * 46)
        if self.step == 0:
            self.app._append_md("Step 1/4: Workspace name? (default: Chat workspace)")
            return
        if self.step == 1:
            self.app._append_md("Step 2/4: Max agents? (default 8)")
            return
        if self.step == 2:
            self.app._append_md("Step 3/4: Max tokens per turn? (default 50000)")
            return
        if self.step == 3:
            self.app._append_md("Step 4/4: Use same model for all roles? (Y/n)")
            return
        if self.step == 4:
            self._ask_role_provider()
            return
        if self.step == 5:
            role = self.roles[self._role_index]
            provider = self.data.get("_role_provider", {}).get(role) or self._default_provider
            self.app._append_md(f"Choose model for {role} (number):")
            self._choose_from_list(self._models_for(provider))
            return
        if self.step == 6:
            role = self.roles[self._role_index]
            if not self._skills:
                self._advance_after_skills([])
                return
            self.app._append_md(f"Select skills for {role} (comma-separated numbers, empty to skip):")
            self._choose_from_list(self._skills_list())
            return

    def _choose_from_list(self, items: list[str]) -> str:
        self.app._append_md(" ")
        for i, item in enumerate(items, 1):
            self.app._append_md(f" {i}. {item}")
        self.app._append_md(" ")
        return ""

    def _providers_list(self) -> list[str]:
        out = []
        for p in self._providers:
            name = p.get("name") or ""
            label = p.get("display_name") or name
            out.append(f"{label} ({name})")
        return out

    def _models_for(self, provider: str) -> list[str]:
        models = self._provider_models.get(provider) or []
        if not models:
            models = self._known_models(provider)
        if not models:
            models = ["default"]
        return models

    def handle_input(self, text: str) -> bool:
        t = (text or "").strip()
        if t.lower() in ("quit", "exit", "cancel"):
            self.app._append_md("[dim]Wizard cancelled.[/dim]")
            return False
        if t.lower() in ("back", "b"):
            if self._pop_state():
                self._prompt_step()
            else:
                self.app._append_md("[dim]Already at the first step.[/dim]")
            return True

        if self.step == 0:
            self._push_state()
            if t.lower() in ("y", "yes"):
                t = ""
            self.data["name"] = t or "Chat workspace"
            self.step = 1
            self._prompt_step()
            return True

        if self.step == 1:
            self._push_state()
            self.data["max_agents"] = int(t) if t.isdigit() else 8
            self.step = 2
            self._prompt_step()
            return True

        if self.step == 2:
            self._push_state()
            self.data["max_tokens"] = int(t) if t.isdigit() else 50000
            self.step = 3
            self._prompt_step()
            return True

        if self.step == 3:
            if t.lower() in ("", "y", "yes"):
                self.data["_reuse_for_all"] = True
            else:
                self.data["_reuse_for_all"] = False
            self._push_state()
            self.step = 4
            self._role_index = 0
            self.data["roles"] = {}
            self._prompt_step()
            return True

        if self.step == 4:
            # role provider selection
            providers = self._providers
            idx = int(t) if t.isdigit() else 0
            if idx < 1 or idx > len(providers):
                self.app._append_md("Invalid choice. Pick a number from the list.")
                return True
            self._push_state()
            provider = providers[idx - 1].get("name") or ""
            role = self.roles[self._role_index]
            self.data.setdefault("_role_provider", {})[role] = provider
            self.step = 5
            self._prompt_step()
            return True

        if self.step == 5:
            role = self.roles[self._role_index]
            provider = self.data.get("_role_provider", {}).get(role) or self._default_provider
            models = self._models_for(provider)
            idx = int(t) if t.isdigit() else 0
            if idx < 1 or idx > len(models):
                self.app._append_md("Invalid choice. Pick a number from the list.")
                return True
            self._push_state()
            model = models[idx - 1]
            self.data["roles"][role] = f"{provider}:{model}"
            self.step = 6
            self._prompt_step()
            return True

        if self.step == 6:
            role = self.roles[self._role_index]
            if not t:
                self._push_state()
                self._set_role_skills(role, [])
                return self._advance_after_skills([])
            picks = [p.strip() for p in t.split(",") if p.strip()]
            idxs = []
            for p in picks:
                if p.isdigit():
                    idxs.append(int(p))
            if not idxs:
                self.app._append_md("Invalid choice. Use numbers separated by commas.")
                return True
            skills = self._skills
            chosen: list[str] = []
            for i in idxs:
                if 1 <= i <= len(skills):
                    skill_id = skills[i - 1].get("id") or ""
                    if skill_id:
                        chosen.append(skill_id)
            self._push_state()
            self._set_role_skills(role, chosen)
            return self._advance_after_skills(chosen)

        return True

    def _ask_role_provider(self) -> None:
        role = self.roles[self._role_index]
        self.app._append_md(f"Choose provider for {role} (number):")
        self._choose_from_list(self._providers_list())

    def _finish(self) -> None:
        self.app._append_md("Creating workspace...")
        roles = self.data.get("roles", {}) or {}
        role_skills = self.data.get("_role_skills", {}) or {}
        lead_spec = roles.get("architect") or next(iter(roles.values()), "")
        lead_provider = self._default_provider
        lead_model = "kilo/auto"
        if ":" in lead_spec:
            lead_provider, lead_model = lead_spec.split(":", 1)
        self.app._create_agi_workspace(
            name=self.data.get("name", "Chat workspace"),
            lead_provider=lead_provider,
            lead_model=lead_model,
            max_agents=self.data.get("max_agents", 8),
            max_tokens=self.data.get("max_tokens", 50000),
            roles=roles,
            role_skills=role_skills,
        )

    def _skills_list(self) -> list[str]:
        out = []
        for s in self._skills:
            name = s.get("name") or s.get("id") or ""
            desc = (s.get("description") or "").strip()
            if desc:
                out.append(f"{name} — {desc[:60]}")
            else:
                out.append(name)
        return out

    def _set_role_skills(self, role: str, skill_ids: list[str]) -> None:
        self.data.setdefault("_role_skills", {})[role] = skill_ids

    def _advance_after_skills(self, chosen: list[str]) -> bool:
        self._role_index += 1
        if self.data.get("_reuse_for_all") and self._role_index >= 1:
            first_role = self.roles[0]
            spec = self.data["roles"].get(first_role)
            if spec:
                for r in self.roles:
                    self.data["roles"][r] = spec
            first_skills = self.data.get("_role_skills", {}).get(first_role, chosen)
            for r in self.roles:
                self._set_role_skills(r, list(first_skills))
            self._finish()
            return False
        if self._role_index >= len(self.roles):
            self._finish()
            return False
        self.step = 4
        self._prompt_step()
        return True


class AGISession:
    def __init__(self, ws_id: str, app_ref=None):
        self.ws_id = ws_id
        self._app_ref = app_ref
        self._cfg_mgr = getattr(app_ref, "config_manager", None) if app_ref else None
        self._init_session()

    def _get_cfg_mgr(self):
        if self._cfg_mgr is None:
            from membria.config import ConfigManager
            self._cfg_mgr = ConfigManager()
        return self._cfg_mgr

    def _get_cfg(self):
        return self._get_cfg_mgr().config

    def _init_session(self) -> None:
        from membria.agi.chat import _load_workspace
        from membria.agi.identity import load_identity
        from membria.agi.cognitive import load_cognitive_template
        from membria.agi.chat import _normalize_model_name
        from membria.graph import GraphClient
        from membria.interactive.providers import ProviderFactory, Message
        from membria.memory_manager import MemoryManager
        from membria.context_manager import ContextManager
        from membria.calibration_updater import CalibrationUpdater
        import httpx

        self.ws = _load_workspace(self.ws_id)
        self.identity = load_identity(self.ws["identity_path"])
        self.template = load_cognitive_template(self.ws["cognitive_template"])

        cfg_mgr = self._get_cfg_mgr()
        cfg = cfg_mgr.config
        self.provider_name = self.ws.get("lead_provider") or cfg.default_provider
        self.lead_model = _normalize_model_name(self.ws.get("lead_model") or cfg.default_model)
        if self.lead_model != self.ws.get("lead_model"):
            try:
                self.ws["lead_model"] = self.lead_model
                from membria.agi.chat import _save_workspace
                _save_workspace(self.ws_id, self.ws)
            except Exception:
                pass
        provider_cfg = cfg.providers.get(self.provider_name, {})
        api_key = provider_cfg.get("api_key") or ""
        endpoint = provider_cfg.get("endpoint")
        auth_token = provider_cfg.get("auth_token")
        auth_method = provider_cfg.get("auth_method")
        if not api_key and not auth_token:
            try:
                resp = httpx.get(
                    "http://localhost:8080/api/user-token",
                    params={"provider": self.provider_name},
                    timeout=3.0,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    auth_token = data.get("token") or auth_token
                    auth_method = data.get("auth_method") or "oauth"
                    if auth_token:
                        cfg_mgr.set(f"providers.{self.provider_name}.auth_token", auth_token)
                        cfg_mgr.set(f"providers.{self.provider_name}.auth_method", auth_method)
            except Exception:
                pass

        graph = GraphClient()
        graph.connect()
        try:
            project_id = self.ws.get("graph_project_id") or cfg.project_id
            if project_id:
                graph._namespace["project_id"] = project_id
        except Exception:
            pass
        self.memory = MemoryManager(graph)
        self.ctx_mgr = ContextManager(graph, CalibrationUpdater())
        self.provider = ProviderFactory.get_provider(self.provider_name, api_key, endpoint, auth_token, auth_method)
        self.history = []
        self.Message = Message
        self._role_name = (getattr(self.identity, "role", None) or getattr(self.identity, "role_name", None) or "architect")
        self._role_links = graph.get_role_links(self._role_name) if graph.connected else {"skills": [], "negative_knowledge": []}
        self._squad_context = ""
        try:
            squad_id = self.ws.get("squad_id") or f"squad_{self.ws_id}"
            assignments = graph.list_assignments(squad_id) if graph.connected else []
            lines = []
            for a in assignments:
                props = getattr(a, "properties", a) or {}
                role_id = props.get("role_id", "") or ""
                role_name = role_id.replace("role_", "", 1) if role_id else ""
                profile_id = props.get("profile_id", "") or ""
                prof = graph.get_profile(profile_id) if profile_id else None
                provider = (prof or {}).get("provider", "")
                model = (prof or {}).get("model", "")
                label = f"{role_name}" if role_name else "role"
                if provider or model:
                    lines.append(f"- {label}: {provider}/{model}")
                else:
                    lines.append(f"- {label}")
            if lines:
                self._squad_context = "SQUAD:\n" + "\n".join(lines) + "\n"
        except Exception:
            self._squad_context = ""
        self._since_last_remember = 0

    async def handle_input(self, user_input: str) -> str:
        from dataclasses import asdict
        from membria.agi.cognitive import build_cognitive_prompt
        from membria.agi.chat import _store_decision, _should_auto_remember, _summarize_turn
        from membria.config import ConfigManager
        from membria.web_search import search_web
        from membria.web_fetch import fetch_headless
        from membria.fs_tools import read_file, list_dir, search_files
        from membria.fs_tools import PathAccessError
        import asyncio
        from rich.markdown import Markdown

        # Researcher-mode pipeline
        try:
            agi_cfg = self._get_cfg().agi or {}
            if agi_cfg.get("research_mode") and not user_input.strip().startswith("/"):
                return await self._run_research_pipeline(
                    user_input,
                    search_web=search_web,
                    fetch_headless=fetch_headless,
                )
        except Exception:
            pass

        tool_result = await self._maybe_tool_call(
            user_input,
            search_web=search_web,
            fetch_headless=fetch_headless,
            read_file=read_file,
            list_dir=list_dir,
            search_files=search_files,
            config=self._get_cfg(),
        )
        if tool_result is not None:
            return tool_result

        if user_input.lower() in ("/exit", "/quit", "/agi exit"):
            return "[dim]Chat session ended. Use Ctrl+G to start again.[/dim]"
        if user_input.startswith("/remember "):
            text = user_input.replace("/remember ", "", 1).strip()
            if text:
                _store_decision(self.memory, text, "manual_remember")
                return "[green]✓ Remembered[/green]"
            return ""
        if user_input.startswith("/forget "):
            dec_id = user_input.replace("/forget ", "", 1).strip()
            if dec_id:
                self.memory.forget_decision(dec_id, "manual_forget")
                return "[green]✓ Forgotten[/green]"
            return ""

        cognitive = build_cognitive_prompt(user_input, asdict(self.identity), self.template)
        ctx = self.ctx_mgr.build_decision_context(
            statement=user_input,
            module="general",
            confidence=0.5,
            max_tokens=int(self.ws.get("max_tokens_per_turn", 4000)),
            role_skills=self._role_links.get("skills"),
            role_negative_knowledge=self._role_links.get("negative_knowledge"),
        )
        system = cognitive + "\n\nCONTEXT:\n" + (self._squad_context or "") + (ctx.get("compact_context") or "")
        messages = [self.Message(role="system", content=system)] + self.history + [self.Message(role="user", content=user_input)]
        response = await self.provider.complete(self.lead_model, messages)
        content = response.content if hasattr(response, "content") else str(response)

        self.history.append(self.Message(role="user", content=user_input))
        self.history.append(self.Message(role="assistant", content=content))
        self.history = self.history[-8:]

        if self.identity.memory_policy.get("auto_remember", True):
            remember_cfg = self.identity.memory_policy or {}
            min_conf = float(remember_cfg.get("min_confidence", 0.7))
            summary_every = int(remember_cfg.get("summary_every", 6))
            should_store, conf = _should_auto_remember(user_input, content)
            if should_store and conf >= min_conf:
                _store_decision(self.memory, f"{user_input}\n\nOUTPUT:\n{content[:2000]}", "auto_remember", confidence=conf)
                self._since_last_remember = 0
                try:
                    if self._app_ref:
                        panel = self._app_ref.query_one("#sidebar", SidePanel)
                        panel.add_decision("Auto-remember", int(conf * 100), True)
                        self._app_ref._refresh_sidebar()
                except Exception:
                    pass
            else:
                self._since_last_remember += 1
                if summary_every > 0 and self._since_last_remember >= summary_every:
                    summary = _summarize_turn(user_input, content)
                    _store_decision(self.memory, summary, "auto_remember_summary", confidence=max(0.6, min_conf))
                    self._since_last_remember = 0
        return content

    async def _run_research_pipeline(self, query: str, search_web, fetch_headless) -> str:
        """Researcher-mode: plan -> search -> synthesize -> red-team -> report."""
        try:
            cfg = self._get_cfg()
            self._ensure_planning_files(query)
            research_cfg = getattr(cfg, "research", {}) or {}
            plan_model = research_cfg.get("plan_model") or self.lead_model
            synth_model = research_cfg.get("synth_model") or self.lead_model
            red_model = research_cfg.get("red_model") or self.lead_model
            final_model = research_cfg.get("final_model") or synth_model
            role_map = research_cfg.get("roles") or ["planner", "synth", "red_team", "final"]
            role_plan = role_map[0] if len(role_map) > 0 else "planner"
            role_synth = role_map[1] if len(role_map) > 1 else "synth"
            role_red = role_map[2] if len(role_map) > 2 else "red_team"
            role_final = role_map[3] if len(role_map) > 3 else "final"

            def _role_context(role_name: str) -> str:
                try:
                    links = self.memory.graph.get_role_links(role_name) if self.memory and self.memory.graph.connected else {}
                    skills = links.get("skills") or []
                    nks = links.get("negative_knowledge") or []
                    lines = []
                    if skills:
                        lines.append("ROLE SKILLS:")
                        for sk in skills[:8]:
                            name = sk.get("name") if isinstance(sk, dict) else str(sk)
                            lines.append(f"- {name}")
                    if nks:
                        lines.append("ROLE NEGATIVE KNOWLEDGE:")
                        for nk in nks[:8]:
                            stmt = nk.get("statement") if isinstance(nk, dict) else str(nk)
                            lines.append(f"- {stmt}")
                    return ("\n".join(lines) + "\n") if lines else ""
                except Exception:
                    return ""

            prompt_plan = (
                "You are a research planner. Return 3-6 bullet subquestions.\n"
                + _role_context(role_plan) +
                f"Question: {query}\n"
                "Return as plain text bullets."
            )
            plan_resp = await self.provider.complete(plan_model, [self.Message(role="user", content=prompt_plan)])
            plan_text = plan_resp.content if hasattr(plan_resp, "content") else str(plan_resp)
            _store_decision(self.memory, f"Research plan:\n{plan_text}", "research_plan", confidence=0.6)

            # Planner gate: decide if tools needed + propose queries/urls
            planner_plan = await self._llm_tool_plan(
                f"{query}\nPlan:\n{plan_text}",
                planner_provider_override="",
                planner_model_override=plan_model,
            )
            if planner_plan:
                _store_decision(self.memory, f"Planner:\n{json.dumps(planner_plan)}", "research_planner", confidence=0.6)
            tool_choice = (planner_plan or {}).get("tool") if planner_plan else "web_search"
            queries = []
            if tool_choice == "none":
                queries = [query]
            elif tool_choice == "web_fetch":
                url = (planner_plan or {}).get("args", {}).get("url") or ""
                if url:
                    queries = [url]
                else:
                    queries = [query]
            else:
                # web_search or fallback
                prompt_queries = (
                    "Convert the plan into 3-6 web search queries. Return one query per line.\n"
                    + _role_context(role_plan) +
                    f"Plan:\n{plan_text}\n"
                )
                q_resp = await self.provider.complete(plan_model, [self.Message(role="user", content=prompt_queries)])
                q_text = q_resp.content if hasattr(q_resp, "content") else str(q_resp)
                queries = [q.strip("-• \t") for q in q_text.splitlines() if q.strip()]
                queries = queries[:6] if queries else [query]

            results_blocks = []
            for q in queries:
                if tool_choice == "web_fetch" and (q.startswith("http://") or q.startswith("https://")):
                    res = fetch_headless(url=q, wait_ms=500, timeout_ms=15000, headless=True)
                    content = (res.content or "").strip()
                    if len(content) > 2000:
                        content = content[:2000] + "…"
                    results_blocks.append(f"Fetch: {q}\n{content}")
                    continue
                results = search_web(q, max_results=3)
                lines = [f"Query: {q}"]
                for r in results:
                    title = r.get("title") or "Untitled"
                    url = r.get("url") or ""
                    snippet = r.get("snippet") or ""
                    lines.append(f"- {title}\n  {url}\n  {snippet}".strip())
                results_blocks.append("\n".join(lines))
            evidence = "\n\n".join(results_blocks)
            _store_decision(self.memory, f"Evidence:\n{evidence[:4000]}", "research_evidence", confidence=0.6)

            prompt_synth = (
                "Synthesize findings into a concise, structured answer. Cite sources by URL where possible.\n"
                + _role_context(role_synth) +
                f"Question: {query}\n"
                f"Evidence:\n{evidence}\n"
            )
            synth_resp = await self.provider.complete(synth_model, [self.Message(role="user", content=prompt_synth)])
            synth_text = synth_resp.content if hasattr(synth_resp, "content") else str(synth_resp)
            _store_decision(self.memory, f"Synthesis:\n{synth_text}", "research_synthesis", confidence=0.7)

            prompt_red = (
                "Red-team the synthesis: list possible errors, missing sources, or conflicting facts.\n"
                + _role_context(role_red) +
                f"Synthesis:\n{synth_text}\n"
            )
            red_resp = await self.provider.complete(red_model, [self.Message(role="user", content=prompt_red)])
            red_text = red_resp.content if hasattr(red_resp, "content") else str(red_resp)
            _store_decision(self.memory, f"Red-team:\n{red_text}", "research_redteam", confidence=0.6)

            prompt_final = (
                "Write the final report using the synthesis and red-team notes. Be concise.\n"
                + _role_context(role_final) +
                f"Question: {query}\n"
                f"Synthesis:\n{synth_text}\n"
                f"Red-team:\n{red_text}\n"
            )
            final_resp = await self.provider.complete(final_model, [self.Message(role="user", content=prompt_final)])
            final_text = final_resp.content if hasattr(final_resp, "content") else str(final_resp)

            final = self._render_research_report(
                query=query,
                plan=plan_text,
                evidence=evidence,
                synthesis=synth_text,
                red_team=red_text,
                final=final_text,
            )
            # Persist to local MD file
            try:
                from pathlib import Path
                import re
                import time as _time
                plan_dir = self._planning_dir()
                slug = re.sub(r"[^a-zA-Z0-9]+", "-", query.strip().lower())[:40].strip("-") or "query"
                ts = _time.strftime("%Y%m%d-%H%M%S")
                name_tpl = (research_cfg.get("output_name_template") or "").strip() if isinstance(research_cfg, dict) else ""
                if not name_tpl:
                    name_tpl = "{ts}_{slug}.md"
                name = name_tpl.format(ts=ts, slug=slug)
                out_path = plan_dir / name
                out_path.write_text(final, encoding="utf-8")
                self._update_verify_log(out_path)
                _store_decision(self.memory, f"Final report saved: {out_path}", "research_report", confidence=0.8)
            except Exception:
                _store_decision(self.memory, f"Final report:\n{final[:4000]}", "research_report", confidence=0.8)
            return final
        except Exception as e:
            return f"[red]Research pipeline failed:[/red] {e}"

    def _ensure_planning_files(self, query: str) -> None:
        try:
            from pathlib import Path
            plan_dir = self._planning_dir()
            files = {
                "PROJECT.md": f"# PROJECT\n\n- Goal: {query}\n- Constraints: \n- Success criteria: \n",
                "PLAN.md": "# PLAN\n\n- \n",
                "STATE.md": "# STATE\n\n- Status: initialized\n",
                "VERIFY.md": "# VERIFY\n\n- [ ] \n",
            }
            for name, content in files.items():
                path = plan_dir / name
                if not path.exists():
                    path.write_text(content, encoding="utf-8")
        except Exception:
            pass

    def _planning_dir(self):
        from membria.agi.workspace import workspace_dir
        ws_dir = workspace_dir(self.ws_id)
        plan_dir = ws_dir / "planning"
        plan_dir.mkdir(parents=True, exist_ok=True)
        return plan_dir

    def _render_research_report(self, **kwargs) -> str:
        try:
            cfg = self._get_cfg()
            research_cfg = getattr(cfg, "research", {}) or {}
            template_path = (research_cfg.get("template_path") or "").strip()
            if template_path:
                from pathlib import Path
                tpl = Path(template_path)
                if tpl.exists():
                    text = tpl.read_text(encoding="utf-8")
                    class SafeDict(dict):
                        def __missing__(self, key):
                            return ""
                    return text.format_map(SafeDict(**kwargs))
        except Exception:
            pass
        return (
            f"## Research Report\n\n"
            f"**Question:** {kwargs.get('query','')}\n\n"
            f"**Plan:**\n{kwargs.get('plan','')}\n\n"
            f"**Evidence:**\n{kwargs.get('evidence','')}\n\n"
            f"**Synthesis:**\n{kwargs.get('synthesis','')}\n\n"
            f"**Red-team:**\n{kwargs.get('red_team','')}\n\n"
            f"**Final:**\n{kwargs.get('final','')}\n"
        )

    def _update_verify_log(self, report_path):
        try:
            from pathlib import Path
            verify = self._planning_dir() / "VERIFY.md"
            if not verify.exists():
                verify.write_text("# VERIFY\n\n", encoding="utf-8")
            rel = Path(report_path).name
            entry = f"- [x] Research report saved: `{rel}`\n"
            with verify.open("a", encoding="utf-8") as f:
                f.write(entry)
        except Exception:
            pass

    async def _maybe_tool_call(
        self,
        user_input: str,
        search_web,
        fetch_headless,
        read_file,
        list_dir,
        search_files,
        config,
    ) -> Optional[str]:
        text = (user_input or "").strip()
        lower = text.lower()
        tools_cfg = getattr(config, "tools", None)
        allowed_paths = getattr(tools_cfg, "allowed_paths", ["~"]) if tools_cfg else ["~"]
        web_search_enabled = bool(getattr(tools_cfg, "web_search_enabled", True)) if tools_cfg else True
        web_fetch_enabled = bool(getattr(tools_cfg, "web_fetch_enabled", True)) if tools_cfg else True
        planner_debug = bool(getattr(tools_cfg, "planner_debug", False)) if tools_cfg else False
        planner_provider_override = getattr(tools_cfg, "planner_provider", "") if tools_cfg else ""
        planner_model_override = getattr(tools_cfg, "planner_model", "") if tools_cfg else ""

        # Explicit tool commands
        if lower.startswith("/websearch ") or lower.startswith("websearch "):
            if not web_search_enabled:
                return "[dim]WebSearch disabled. Enable with: membria config set tools.web_search_enabled true[/dim]"
            query = text.split(" ", 1)[1].strip()
            results = search_web(query, max_results=5)
            if not results:
                return "[dim]No results.[/dim]"
            lines = ["[bold]WebSearch results:[/bold]"]
            for r in results:
                title = r.get("title") or "Untitled"
                url = r.get("url") or ""
                snippet = r.get("snippet") or ""
                lines.append(f"- {title}\n  {url}")
                if snippet:
                    lines.append(f"  {snippet}")
            return "\n".join(lines)

        if lower.startswith("/webfetch ") or lower.startswith("webfetch "):
            if not web_fetch_enabled:
                return "[dim]WebFetch disabled. Enable with: membria config set tools.web_fetch_enabled true[/dim]"
            url = text.split(" ", 1)[1].strip()
            try:
                res = fetch_headless(url=url, wait_ms=500, timeout_ms=15000, headless=True)
                title = res.title or ""
                content = (res.content or "").strip()
                if len(content) > 2000:
                    content = content[:2000] + "…"
                out = f"[bold]Fetched:[/bold] {res.url}"
                if title:
                    out += f"\n[dim]{title}[/dim]"
                return out + "\n\n" + content
            except Exception as e:
                return f"[red]WebFetch failed:[/red] {e}"

        if lower.startswith("/read "):
            path = text.split(" ", 1)[1].strip()
            try:
                data = read_file(path=path, allowed_paths=allowed_paths)
                content = data.get("content", "")
                if data.get("truncated"):
                    content += "\n[dim](truncated)[/dim]"
                return f"[bold]{data.get('path')}[/bold]\n\n{content}"
            except PathAccessError as e:
                return f"[red]Read failed:[/red] {e}"

        if lower.startswith("/ls "):
            path = text.split(" ", 1)[1].strip()
            try:
                data = list_dir(path=path, allowed_paths=allowed_paths, recursive=False, limit=200)
                entries = data.get("entries", [])
                if not entries:
                    return "[dim]Empty directory.[/dim]"
                lines = [f"[bold]{data.get('path')}[/bold]"]
                for e in entries[:80]:
                    lines.append(f"- {e.get('path')}")
                if len(entries) > 80:
                    lines.append("[dim]...truncated[/dim]")
                return "\n".join(lines)
            except PathAccessError as e:
                return f"[red]List failed:[/red] {e}"

        if lower.startswith("/grep "):
            # /grep query path
            parts = text.split(" ", 2)
            if len(parts) < 3:
                return "[dim]Usage: /grep <query> <path>[/dim]"
            query = parts[1].strip()
            path = parts[2].strip()
            try:
                data = search_files(query=query, path=path, allowed_paths=allowed_paths, max_results=50)
                matches = data.get("matches", [])
                if not matches:
                    return "[dim]No matches.[/dim]"
                lines = [f"[bold]Matches in {data.get('path')}[/bold]"]
                for m in matches:
                    lines.append(f"- {m.get('path')}:{m.get('lineno')}: {m.get('line')}")
                return "\n".join(lines)
            except PathAccessError as e:
                return f"[red]Search failed:[/red] {e}"

        # Heuristic web search for natural language (rules-first)
        auto_triggers = (
            "в интернете",
            "поищи",
            "найди",
            "search",
            "курс",
            "exchange rate",
            "usd",
            "eur",
            "btc",
            "погода",
        )
        if web_search_enabled and any(t in lower for t in auto_triggers):
            try:
                results = search_web(text, max_results=5)
                if not results:
                    return "[dim]No results.[/dim]"
                lines = ["[bold]WebSearch results:[/bold]"]
                for r in results:
                    title = r.get("title") or "Untitled"
                    url = r.get("url") or ""
                    snippet = r.get("snippet") or ""
                    lines.append(f"- {title}\n  {url}")
                    if snippet:
                        lines.append(f"  {snippet}")
                return "\n".join(lines)
            except Exception as e:
                return f"[red]WebSearch failed:[/red] {e}"

        # LLM planner (only when rules are unsure)
        planner_enabled = bool(getattr(tools_cfg, "planner_enabled", True)) if tools_cfg else True
        if planner_enabled:
            plan = await self._llm_tool_plan(
                text,
                planner_provider_override=planner_provider_override,
                planner_model_override=planner_model_override,
            )
            if plan:
                tool = plan.get("tool")
                args = plan.get("args") or {}
                reason = plan.get("reason") or ""
                debug_line = ""
                if planner_debug:
                    arg_hint = ""
                    if tool in ("web_search", "web_fetch"):
                        arg_hint = args.get("query") or args.get("url") or ""
                    debug_line = f"[dim]Planner: {tool} {arg_hint}[/dim]\n" + (f"[dim]{reason}[/dim]\n" if reason else "")
                if tool == "web_search" and web_search_enabled:
                    query = args.get("query") or text
                    results = search_web(query, max_results=5)
                    if not results:
                        return "[dim]No results.[/dim]"
                    lines = ["[bold]WebSearch results:[/bold]"]
                    for r in results:
                        title = r.get("title") or "Untitled"
                        url = r.get("url") or ""
                        snippet = r.get("snippet") or ""
                        lines.append(f"- {title}\n  {url}")
                        if snippet:
                            lines.append(f"  {snippet}")
                    return debug_line + "\n".join(lines)
                if tool == "web_fetch" and web_fetch_enabled:
                    url = args.get("url")
                    if not url:
                        return "[dim]WebFetch needs a url.[/dim]"
                    res = fetch_headless(url=url, wait_ms=500, timeout_ms=15000, headless=True)
                    title = res.title or ""
                    content = (res.content or "").strip()
                    if len(content) > 2000:
                        content = content[:2000] + "…"
                    out = f"[bold]Fetched:[/bold] {res.url}"
                    if title:
                        out += f"\n[dim]{title}[/dim]"
                    return debug_line + out + "\n\n" + content
                if tool == "read_file":
                    path = args.get("path")
                    if not path:
                        return "[dim]Read needs a path.[/dim]"
                    try:
                        data = read_file(path=path, allowed_paths=allowed_paths)
                        content = data.get("content", "")
                        if data.get("truncated"):
                            content += "\n[dim](truncated)[/dim]"
                        return debug_line + f"[bold]{data.get('path')}[/bold]\n\n{content}"
                    except PathAccessError as e:
                        return f"[red]Read failed:[/red] {e}"
                if tool == "list_dir":
                    path = args.get("path")
                    if not path:
                        return "[dim]List needs a path.[/dim]"
                    try:
                        data = list_dir(path=path, allowed_paths=allowed_paths, recursive=False, limit=200)
                        entries = data.get("entries", [])
                        if not entries:
                            return "[dim]Empty directory.[/dim]"
                        lines = [f"[bold]{data.get('path')}[/bold]"]
                        for e in entries[:80]:
                            lines.append(f"- {e.get('path')}")
                        if len(entries) > 80:
                            lines.append("[dim]...truncated[/dim]")
                        return debug_line + "\n".join(lines)
                    except PathAccessError as e:
                        return f"[red]List failed:[/red] {e}"
                if tool == "search_files":
                    query = args.get("query")
                    path = args.get("path")
                    if not query or not path:
                        return "[dim]Search needs query + path.[/dim]"
                    try:
                        data = search_files(query=query, path=path, allowed_paths=allowed_paths, max_results=50)
                        matches = data.get("matches", [])
                        if not matches:
                            return "[dim]No matches.[/dim]"
                        lines = [f"[bold]Matches in {data.get('path')}[/bold]"]
                        for m in matches:
                            lines.append(f"- {m.get('path')}:{m.get('lineno')}: {m.get('line')}")
                        return debug_line + "\n".join(lines)
                    except PathAccessError as e:
                        return f"[red]Search failed:[/red] {e}"

        return None

    async def _llm_tool_plan(
        self,
        text: str,
        planner_provider_override: str = "",
        planner_model_override: str = "",
    ) -> Optional[dict]:
        """Cheap planner: decide if a tool is needed and which one."""
        try:
            cfg_mgr = ConfigManager()
            cfg = cfg_mgr.config
            providers = cfg.providers or {}
            planner_provider = planner_provider_override or None
            # Prefer enabled providers with credentials
            if not planner_provider:
                for name, p in providers.items():
                    if not p.get("enabled"):
                        continue
                    if p.get("api_key") or p.get("auth_token"):
                        planner_provider = name
                        break
            if not planner_provider:
                return None
            planner_model = planner_model_override or providers.get(planner_provider, {}).get("model") or ("kilo/auto" if planner_provider == "kilo" else "")
            p_cfg = providers.get(planner_provider, {})
            provider = ProviderFactory.get_provider(
                planner_provider,
                p_cfg.get("api_key"),
                p_cfg.get("endpoint"),
                p_cfg.get("auth_token"),
                p_cfg.get("auth_method"),
            )
            prompt = (
                "Decide if a tool is needed. Reply ONLY JSON.\n"
                "Tools: web_search(query), web_fetch(url), read_file(path), list_dir(path), search_files(query,path), none.\n"
                f"User: {text}\n"
                "JSON: {\"tool\":\"web_search|web_fetch|read_file|list_dir|search_files|none\",\"args\":{...},\"reason\":\"short\"}"
            )
            msgs = [self.Message(role="user", content=prompt)]
            resp = await provider.complete(planner_model, msgs)
            raw = resp.content if hasattr(resp, "content") else str(resp)
            try:
                data = json.loads(raw.strip())
                if isinstance(data, dict) and data.get("tool") and data.get("tool") != "none":
                    return data
            except Exception:
                return None
        except Exception:
            return None
        return None



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
            yield Static("[bold]Membria[/bold] ▸", id="inp-prompt")
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
    SUB_TITLE = ""
    DEFAULT_CSS = "App { background: #2e3440; }"

    BINDINGS = [
        Binding("ctrl+d", "quit", "Quit"),
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+l", "clear_output", "Clear"),
        Binding("ctrl+m", "toggle_mouse", "Mouse"),
        Binding("ctrl+p", "open_providers", "Providers"),
        Binding("ctrl+i", "focus_input", "Focus"),
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
        background: #2e3440;
    }

    /* ── Header ── */
    Header {
        dock: top;
        height: 1;
        background: $background;
        border-bottom: solid #88C0D0 60%;
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
        border-right: solid #88C0D0 30%;
        overflow-y: auto;
        scrollbar-color: $primary 0%;
        scrollbar-color-hover: $primary 20%;
        scrollbar-background: $background;
        scrollbar-size: 1 1;
        padding: 0 1;
    }

    #main-top {
        layout: horizontal;
        height: auto;
        background: $background;
        padding: 1 0 0 0;
    }

    #main-title {
        width: 14;
        height: auto;
        padding: 0 1 0 1;
    }

    #top-info {
        width: 1fr;
        height: auto;
        padding: 1 1 0 2;
        color: $text;
    }

    #main-title-spacer {
        height: 1;
    }

    /* ── Sidebar ── */
    #sidebar {
        width: 34;
        height: 1fr;
        background: $panel;
        padding: 1 1 1 1;
        layout: vertical;
        overflow-y: auto;
        scrollbar-color: $primary 0%;
        scrollbar-color-hover: $primary 20%;
        scrollbar-background: $panel;
        scrollbar-size: 1 1;
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

    #panel-workspace,
    #panel-roles,
    #panel-skills,
    #panel-session,
    #panel-decisions {
        height: auto;
        padding: 0 0 1 1;
    }

    .panel-divider {
        height: 1;
        margin: 1 0 0 0;
        color: #4C566A;
    }

    /* ── Input row ── */
    #input-container {
        height: 3;
        background: $panel;
        border-top: solid #88C0D0 50%;
        border-bottom: solid #88C0D0 50%;
        padding: 0;
    }

    /* Text wizard runs in output; no modal styles. */

    #inp-row {
        height: 3;
        padding: 0 1;
    }

    #inp-prompt {
        width: auto;
        height: 1;
        margin-top: 0;
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
        border-top: solid #88C0D0 30%;
        border-bottom: solid #88C0D0 30%;
        padding: 0 1;
        color: $foreground;
        content-align: left middle;
    }

    /* ── Footer ── */
    Footer {
        dock: bottom;
        background: $panel;
        border-top: solid #88C0D0 40%;
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
        self._text_wizard = None
        self._focus_enabled = True

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
        with Horizontal(id="main"):
            with Vertical(id="main-left"):
                with Horizontal(id="main-top"):
                    indent = "   "
                    ansi_logo = (
                        f"{indent}\x1b[38;5;33m█     █\x1b[0m\x1b[38;5;27m▒░\x1b[0m\n"
                        f"{indent}\x1b[38;5;33m██   ██\x1b[0m\x1b[38;5;27m▒░\x1b[0m\n"
                        f"{indent}\x1b[38;5;33m█ █ █ █\x1b[0m\x1b[38;5;27m▒░\x1b[0m\n"
                        f"{indent}\x1b[38;5;33m█  █  █\x1b[0m\x1b[38;5;27m▒░\x1b[0m\n"
                        f"{indent}\x1b[38;5;33m█     █\x1b[0m\x1b[38;5;27m▒░\x1b[0m"
                    )
                    lines = ansi_logo.splitlines()
                    combined = Text()
                    if lines:
                        combined.append(Text.from_ansi(lines[0]))
                        for line in lines[1:]:
                            combined.append("\n")
                            combined.append(Text.from_ansi(line))
                    yield Static(combined, id="main-title")
                    yield Static("", id="top-info")
                yield Static("", id="main-title-spacer")
                self.output = RichLog(id="output", markup=True, highlight=True, wrap=True)
                yield self.output
            yield SidePanel(id="sidebar", config_manager=self.config_manager)

        yield InputContainer(id="input-container")

        self.status_bar = StatusBar(id="status-bar")
        yield self.status_bar

        # No Footer — it would cover the status bar; keybindings shown in header

    async def on_mount(self) -> None:
        self.theme = "nord"

        # Disable mouse reporting by default to allow selection/copy.
        try:
            driver = getattr(self, "_driver", None)
            if driver and getattr(driver, "_mouse", True):
                driver._mouse = False
                if hasattr(driver, "_disable_mouse_support"):
                    driver._disable_mouse_support()
        except Exception:
            pass

        self._md_buffer = ""

        # No banner in output; header already shows "Membria".

        if not self.skip_splash:
            try:
                self.push_screen(SplashScreen())
            except Exception:
                pass

        # Start MCP in a real background thread — urlopen blocks the event loop
        def _start_mcp_thread():
            try:
                self._ensure_mcp_started(force=True)
            except Exception:
                pass
            try:
                self._ensure_mcp_front_started(force=True)
            except Exception:
                pass

        import threading
        threading.Thread(target=_start_mcp_thread, daemon=True).start()

        if self.config_manager.is_first_run():
            try:
                from .onboarding_screens import OnboardingFlow
                flow = OnboardingFlow(self, self.config_manager)
                flow.start()
                while len(self.screen_stack) > 1:
                    await asyncio.sleep(0.1)
            except Exception:
                pass

        # Periodic sidebar refresh — only fast local checks, no network I/O
        self.set_interval(30.0, self._refresh_sidebar)

        # Auto-show onboarding tips or compact help on startup
        try:
            if not self._md_buffer:
                self._show_startup_help()
        except Exception:
            pass

        pass  # config watch removed — was doing file I/O every second in event loop

    def _watch_config(self) -> None:
        try:
            cfg_path = self.config_manager.config_file
            mtime = cfg_path.stat().st_mtime if cfg_path.exists() else 0
            last = getattr(self, "_cfg_mtime", 0)
            if mtime > last:
                setattr(self, "_cfg_mtime", mtime)
                self.config_manager.reload()
                # Re-sync any runtime state if needed
                self._refresh_sidebar()
        except Exception:
            pass

    def _ensure_mcp_started(self, force: bool = False) -> None:
        try:
            from membria.process_manager import ProcessManager
            cfg = self.config_manager.config if self.config_manager else None
            daemon_cfg = getattr(cfg, "daemon", None)
            auto_start = False
            port = 3117
            if isinstance(daemon_cfg, dict):
                auto_start = bool(daemon_cfg.get("auto_start", False))
                port = int(daemon_cfg.get("port", 3117))
            else:
                auto_start = bool(getattr(daemon_cfg, "auto_start", False))
                port = int(getattr(daemon_cfg, "port", 3117))
            if not (cfg and daemon_cfg and auto_start):
                return
            manager = ProcessManager()
            if force and manager.is_running():
                return
            now = time.time()
            last = getattr(self, "_last_mcp_start_attempt", 0)
            if force or (now - last > 10):
                setattr(self, "_last_mcp_start_attempt", now)
                if not manager.is_running():
                    ok, msg = manager.start(port=port)
                    if not ok:
                        setattr(self, "_mcp_last_error", msg)
                        setattr(self, "_mcp_error_reported", False)
        except Exception as e:
            try:
                self._append_md(f"[#BF616A]MCP start exception:[/#BF616A] {str(e)[:120]}")
            except Exception:
                pass

    def _ensure_mcp_front_started(self, force: bool = False) -> None:
        try:
            cfg = self.config_manager.config if self.config_manager else None
            mcp_front_cfg = getattr(cfg, "mcp_front", None) if cfg else None
            now = time.time()
            last = getattr(self, "_last_mcp_front_start_attempt", 0)
            if not force and (now - last) < 10:
                return
            setattr(self, "_last_mcp_front_start_attempt", now)

            # Quick probe
            try:
                import urllib.request
                base = getattr(mcp_front_cfg, "base_url", "http://localhost:8080") if mcp_front_cfg else "http://localhost:8080"
                urllib.request.urlopen(f"{base.rstrip('/')}/api/providers", timeout=1.0)
                return
            except Exception:
                pass

            # Start via script
            from pathlib import Path
            script = Path(__file__).resolve().parents[3] / "scripts" / "mcp-front.sh"
            if script.exists():
                subprocess.Popen([str(script), "start"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    def _show_startup_help(self) -> None:
        try:
            cfg = self.config_manager.config if self.config_manager else None
            onboarding_done = False
            try:
                onboarding_done = bool(getattr(cfg, "onboarding", {}).get("completed")) if cfg else False
            except Exception:
                onboarding_done = False
            first_run = self.config_manager.is_first_run() if self.config_manager else False
            if first_run or not onboarding_done:
                self._append_md("[bold]Welcome to Membria[/bold]")
                self._append_md("")
                self._append_md("First steps:")
                self._append_md("1. Configure providers: [bold]membria connect[/bold] (or open /my/tokens)")
                self._append_md("2. Start chat: [bold]membria chat[/bold]")
                self._append_md("3. Optional research mode: [bold]/research on[/bold]")
                self._append_md("")
                self._append_md("Type [bold]/help[/bold] for full commands.")
            else:
                self._append_md("[dim]Type /help for commands. Use /research on to enable research mode.[/dim]")
        except Exception:
            pass

    def _refresh_sidebar(self) -> None:
        """Refresh sidebar — only fast local calls, no network I/O."""
        try:
            panel = self.query_one("#sidebar", SidePanel)
            panel._refresh_workspace()
            panel._refresh_roles()
            panel._refresh_session_local()
            self._refresh_top_info(panel)
        except Exception:
            pass

    def _refresh_top_info(self, panel: SidePanel) -> None:
        """Update top info bar — local data only, no network I/O."""
        try:
            cfg = getattr(self.config_manager, "config", None)
            project_id = getattr(cfg, "project_id", "default") if cfg else "default"
            team_id = getattr(cfg, "team_id", "default") if cfg else "default"
            mode = "pipeline"
            try:
                mode = cfg.get("orchestration", {}).get("mode", "pipeline") if cfg else "pipeline"
            except Exception:
                pass
            ws_id = getattr(self, "_active_ws_id", "") or ""
            ws_part = f"  [dim]ws:[/dim] {ws_id}" if ws_id else ""
            text = (
                f"[bold]Project:[/bold] {project_id}   [bold]Team:[/bold] {team_id}{ws_part}\n"
                f"[dim]Mode:[/dim] {mode}"
            )
            self.query_one("#top-info", Static).update(text)
        except Exception:
            pass

    async def on_input_container_user_submit(self, msg: InputContainer.UserSubmit) -> None:
        text = msg.text
        if getattr(self, "_text_wizard", None):
            self._append_md(" ")
            self._append_md(f"[bold #88C0D0]▸[/bold #88C0D0] [bold]{text}[/bold]")
            self._append_md(" ")
        else:
            self._append_md(f"[bold #88C0D0]▸[/bold #88C0D0] [bold]{text}[/bold]")

        try:
            if self._text_wizard:
                keep = self._text_wizard.handle_input(text)
                if not keep:
                    self._text_wizard = None
                self.focus_input()
                return
            if text.startswith("/"):
                # Allow AGI tool commands to be handled inside AGI session
                if getattr(self, "_agi_session", None) and text.lower().startswith(("/websearch", "/webfetch", "/read ", "/ls ", "/grep ")):
                    result = await self._agi_session.handle_input(text)
                    if result:
                        self._append_md("[#4C566A]──────────────────────────────[/#4C566A]")
                        self._append_md(result)
                        self._append_md("[#4C566A]──────────────────────────────[/#4C566A]")
                else:
                    result = await self.command_handler.handle_command(text)
                    if result:
                        self._append_md(result)
            elif text.strip() == "membria chat":
                self._start_ozar_chat()
            elif text.startswith("membria chat "):
                cmd = text.strip().lower()
                if cmd.endswith(" setup"):
                    self.action_open_agi_wizard()
                elif cmd.endswith(" chat"):
                    self._start_ozar_chat()
                else:
                    self._append_md("[dim]Usage: membria chat setup | membria chat[/dim]")
            elif text.startswith("membria "):
                # Run raw CLI command inside the TUI
                try:
                    cmd = shlex.split(text)
                    completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
                    output = (completed.stdout or "") + (completed.stderr or "")
                    # Strip mouse-reporting control codes from embedded CLI output
                    output = re.sub(r"\x1b\[\?100[026]l", "", output)
                    if not output.strip():
                        output = f"[dim]Command exited with {completed.returncode}[/dim]"
                    self._append_md(output)
                except Exception as e:
                    self._append_md(f"[#BF616A]✗ Command failed:[/#BF616A] {e}")
            else:
                if getattr(self, "_agi_session", None):
                    result = await self._agi_session.handle_input(text)
                    if result:
                        self._append_md("[#4C566A]──────────────────────────────[/#4C566A]")
                        self._append_md(result)
                        self._append_md("[#4C566A]──────────────────────────────[/#4C566A]")
                else:
                    result = await self.executor.run_orchestration(text)
                    if result:
                        self._append_md("[#4C566A]──────────────────────────────[/#4C566A]")
                        self._append_md(result)
                        self._append_md("[#4C566A]──────────────────────────────[/#4C566A]")
        except Exception as e:
            self._append_md(f"[#BF616A]✗ Error:[/#BF616A] {e}")

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
            self._refresh_sidebar()
            self.focus_input()
        except Exception:
            pass

    def action_open_providers(self) -> None:
        self.open_providers_screen()

    def open_providers_screen(self) -> None:
        try:
            self.push_screen(ProvidersScreen(self))
        except Exception:
            try:
                self._append_md("[#BF616A]✗ Failed to open providers screen[/#BF616A]")
            except Exception:
                pass

    def focus_input(self) -> None:
        try:
            self.query_one("#inp", Input).focus()
        except Exception:
            pass

    def _append_md(self, content) -> None:
        try:
            from rich.markdown import Markdown
            from rich.console import RenderableType
            import re
            if isinstance(content, Markdown):
                self.output.write(content)
                return
            text = str(content)
            if not text.strip():
                return
            # If this is Rich markup, strip only rich-style tags and keep Markdown
            if "[" in text and "]" in text:
                rich_tag = r"\[(?:/)?(?:dim|bold|red|green|yellow|blue|magenta|cyan|white|black|#[0-9A-Fa-f]{3,8})(?: [^\]]+)?\]"
                text = re.sub(rich_tag, "", text)
            # Treat as Markdown by default
            self.output.write(Markdown(text))
        except Exception:
            pass

    def _bubble_width(self) -> int:
        try:
            sidebar = 34
            width = max(34, min(90, (self.size.width or 100) - sidebar - 6))
            return width
        except Exception:
            return 60

    def _format_bubble(self, label: str, text: str) -> str:
        return str(text or "")

    def _start_ozar_chat(self) -> None:
        try:
            from membria.config import ConfigManager
            from membria.agi.workspace import workspace_dir
            from pathlib import Path
            # Prefer active ws from app state
            ws_id = getattr(self, "_active_ws_id", "") or ""
            cfg = ConfigManager()
            if not ws_id:
                ws_id = cfg.get("agi.active_ws_id")
            if not ws_id:
                # find latest workspace (singleton reuse)
                root = Path.home() / ".membria" / "workspaces"
                if root.exists():
                    entries = [p for p in root.iterdir() if p.is_dir() and p.name.startswith("ws_")]
                    if entries:
                        latest = max(entries, key=lambda p: p.stat().st_mtime)
                        meta_path = latest / "workspace.json"
                        if meta_path.exists():
                            data = json.loads(meta_path.read_text(encoding="utf-8"))
                            ws_id = data.get("id") or latest.name
            if not ws_id:
                # Auto-create singleton workspace
                try:
                    from membria.agi.workspace import create_workspace, workspace_dir
                    from membria.agi.identity import resolve_identity_path
                    from membria.agi.cognitive import resolve_cognitive_template_path
                    from membria.graph import GraphClient
                    cfg_mgr = ConfigManager()
                    cfg2 = cfg_mgr.config
                    graph = GraphClient()
                    if not graph.connect():
                        self._append_md("[dim]No workspace (graph not connected).[/dim]")
                        return
                    identity_path = resolve_identity_path(str(Path(__file__).resolve().parents[3] / "prompts" / "identities" / "pragmatic.yaml"))
                    cognitive_path = resolve_cognitive_template_path(str(Path(__file__).resolve().parents[3] / "prompts" / "cognitive_core.md"))
                    ws = create_workspace(
                        graph=graph,
                        name="Chat workspace",
                        lead_model=cfg2.default_model,
                        identity_path=identity_path,
                        max_agents=8,
                        max_tokens_per_turn=50000,
                    )
                    meta = {
                        "id": ws.id,
                        "name": ws.name,
                        "lead_model": ws.lead_model,
                        "lead_provider": cfg2.default_provider,
                        "max_agents": ws.max_agents,
                        "max_tokens_per_turn": ws.max_tokens_per_turn,
                        "identity_path": identity_path,
                        "cognitive_template": cognitive_path,
                        "graph_workspace_id": ws.id,
                        "graph_project_id": f"proj_{ws.id}",
                    }
                    ws_dir = workspace_dir(ws.id)
                    ws_dir.mkdir(parents=True, exist_ok=True)
                    (ws_dir / "workspace.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
                    cfg_mgr.set("agi.active_ws_id", ws.id)
                    ws_id = ws.id
                except Exception as e:
                    self._append_md(f"[dim]No workspace (auto-create failed): {e}[/dim]")
                    return
            try:
                cfg.set("agi.active_ws_id", ws_id)
            except Exception:
                pass
            self._agi_session = AGISession(ws_id, self)
            self._active_ws_id = ws_id
            self._append_md(f"[#A3BE8C]✓ Chat started[/#A3BE8C] ({ws_id})")
            self.focus_input()
            self._refresh_sidebar()
        except Exception as e:
            self._append_md(f"[#BF616A]✗ Failed to start chat:[/#BF616A] {e}")

    def action_open_agi_wizard(self) -> None:
        try:
            self.open_agi_wizard()
        except Exception:
            try:
                self._append_md("[#BF616A]✗ Failed to open chat setup[/#BF616A]")
            except Exception:
                pass

    def open_agi_wizard(self) -> None:
        try:
            self._text_wizard = TextWizard(self)
            self._text_wizard.start()
        except Exception:
            pass

    def close_agi_wizard(self) -> None:
        try:
            self._text_wizard = None
            self.focus_input()
        except Exception:
            pass

    def _ensure_input_focus(self) -> None:
        if not getattr(self, "_focus_enabled", True):
            return
        try:
            if self.screen and self.screen.id in ("providers",):
                return
        except Exception:
            pass
        try:
            inp = self.query_one("#inp", Input)
            if not inp.has_focus:
                inp.focus()
        except Exception:
            pass

    def action_clear_output(self) -> None:
        self._md_buffer = ""
        try:
            self.query_one("#output", RichLog).clear()
        except Exception:
            pass

    def _create_agi_workspace(
        self,
        name: str,
        lead_provider: str,
        lead_model: str,
        max_agents: int,
        max_tokens: int,
        roles: dict,
        role_skills: dict | None = None,
    ) -> None:
        try:
            from membria.config import ConfigManager
            from membria.agi.workspace import create_workspace, workspace_dir
            from membria.agi.identity import resolve_identity_path
            from membria.agi.cognitive import resolve_cognitive_template_path
            from membria.graph import GraphClient
            cfg_mgr = ConfigManager()
            cfg = cfg_mgr.config
            if lead_provider == "kilo-code":
                lead_provider = "kilo"
            identity_path = resolve_identity_path(str(Path(__file__).resolve().parents[3] / "prompts" / "identities" / "pragmatic.yaml"))
            cognitive_path = resolve_cognitive_template_path(str(Path(__file__).resolve().parents[3] / "prompts" / "cognitive_core.md"))

            graph = GraphClient()
            if not graph.connect():
                self._append_md("[#BF616A]✗ Failed to connect to graph[/#BF616A]")
                return
            project_id = f"proj_{ws.id}"
            try:
                graph._namespace["project_id"] = project_id
            except Exception:
                pass

            ws = create_workspace(
                graph=graph,
                name=name,
                lead_model=lead_model,
                identity_path=identity_path,
                max_agents=max_agents,
                max_tokens_per_turn=max_tokens,
            )

            meta = {
                "id": ws.id,
                "name": ws.name,
                "lead_model": lead_model,
                "lead_provider": lead_provider,
                "max_agents": ws.max_agents,
                "max_tokens_per_turn": ws.max_tokens_per_turn,
                "identity_path": identity_path,
                "cognitive_template": cognitive_path,
                "graph_workspace_id": ws.id,
                "graph_project_id": project_id,
                "role_skills": role_skills or {},
            }
            ws_dir = workspace_dir(ws.id)
            ws_dir.mkdir(parents=True, exist_ok=True)
            (ws_dir / "workspace.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

            # Save role assignments (best-effort)
            team = cfg_mgr.config.team or {}
            team_agents = team.get("agents") or {}
            for role, spec in (roles or {}).items():
                if not spec:
                    continue
                if ":" in spec:
                    prov, mod = spec.split(":", 1)
                    if prov.strip() == "kilo-code":
                        prov = "kilo"
                    team_agents[role] = {"provider": prov.strip(), "model": mod.strip(), "label": role}
            team["agents"] = team_agents
            cfg_mgr.config.team = team
            cfg_mgr.set("agi.active_ws_id", ws.id)

            # Link role skills in graph (best-effort)
            for role, skills in (role_skills or {}).items():
                for skill_id in skills or []:
                    try:
                        graph.link_role_skill(role, skill_id)
                    except Exception:
                        pass

            # Create squad + assignments + profiles in graph
            try:
                squad_id = f"squad_{ws.id}"
                graph.create_squad(squad_id, name=ws.name, strategy="agi", project_id=project_id)
                meta["squad_id"] = squad_id
                order = 0
                for role, spec in (roles or {}).items():
                    if not spec:
                        continue
                    role_id = f"role_{role}"
                    graph.upsert_role(role_id, role)
                    prov, mod = ("", "")
                    if ":" in spec:
                        prov, mod = spec.split(":", 1)
                    if prov.strip() == "kilo-code":
                        prov = "kilo"
                    profile_id = f"prof_{ws.id}_{role}"
                    graph.upsert_profile(
                        profile_id=profile_id,
                        name=f"{ws.name}:{role}",
                        config_path=str(ws_dir / "workspace.json"),
                        provider=prov.strip(),
                        model=mod.strip(),
                    )
                    assignment_id = f"asn_{ws.id}_{role}"
                    graph.add_assignment(
                        assignment_id=assignment_id,
                        squad_id=squad_id,
                        role_id=role_id,
                        profile_id=profile_id,
                        order=order,
                        weight=1.0,
                    )
                    order += 1
            except Exception:
                pass

            self._agi_session = AGISession(ws.id, self)
            self._active_ws_id = ws.id
            self._append_md(f"[#A3BE8C]✓ Workspace ready:[/#A3BE8C] {ws.id}")
            self._append_md("[#A3BE8C]✓ Chat setup complete[/#A3BE8C]")
            self.focus_input()
            self._refresh_sidebar()
        except Exception as e:
            self._append_md(f"[#BF616A]✗ Failed to create workspace:[/#BF616A] {e}")

    def action_toggle_mouse(self) -> None:
        driver = getattr(self, "_driver", None)
        if not driver:
            return
        if getattr(driver, "_mouse", True):
            driver._mouse = False
            if hasattr(driver, "_disable_mouse_support"):
                driver._disable_mouse_support()
            try:
                self._append_md("[dim]Mouse disabled (terminal selection enabled). Ctrl+M to re-enable.[/dim]")
            except Exception:
                pass
        else:
            driver._mouse = True
            if hasattr(driver, "_enable_mouse_support"):
                driver._enable_mouse_support()
            try:
                self._append_md("[dim]Mouse enabled (UI click). Ctrl+M to disable for selection.[/dim]")
            except Exception:
                pass

def run_textual_shell(config_manager, skip_splash: bool = False):
    """Launch Membria TUI."""
    # Textual sends \033[?2026$p and \033[?2048$p (terminal capability queries)
    # which macOS terminals that don't support them render as a literal 'p'.
    # Patch both methods out so neither sequence is ever written.
    try:
        from textual.drivers import linux_driver
        linux_driver.LinuxDriver._request_terminal_sync_mode_support = lambda self: None
        linux_driver.LinuxDriver._query_in_band_window_resize = lambda self: None
    except Exception:
        pass

    app = MembriaApp(config_manager)
    app.skip_splash = skip_splash

    def sig_handler(signum, frame):
        app.exit()

    original = signal.signal(signal.SIGINT, sig_handler)
    try:
        app.run()
    finally:
        signal.signal(signal.SIGINT, original)
