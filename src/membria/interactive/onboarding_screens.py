"""
Textual-based onboarding screens for Membria CLI.
Creates modal dialogs and screens for interactive setup on first launch.
"""

import asyncio
import json
import subprocess
import webbrowser
import os
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import threading
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, Button, Input, Label, OptionList, RadioButton, RadioSet
from textual.screen import Screen
from textual.message import Message


class OnboardingScreen(Screen):
    """Base onboarding screen with progress tracking."""
    
    DEFAULT_CSS = """
    OnboardingScreen {
        align: center middle;
    }
    
    OnboardingScreen > Container {
        width: 80;
        height: auto;
        border: solid $primary;
        background: $surface;
    }
    
    OnboardingScreen .title {
        dock: top;
        height: 3;
        content-align: center middle;
        color: $primary;
        text-style: bold;
    }
    
    OnboardingScreen .progress {
        dock: top;
        height: 1;
        text-style: dim;
        color: $secondary;
    }
    
    OnboardingScreen .content {
        height: auto;
        overflow-y: auto;
        padding: 1 2;
    }
    
    OnboardingScreen .actions {
        dock: bottom;
        height: auto;
        layout: horizontal;
        align: right bottom;
        padding: 1 2;
    }
    
    OnboardingScreen Button {
        margin: 0 1;
    }
    
    OnboardingScreen Input {
        margin: 0 0 1 0;
    }
    """
    
    BINDINGS = [("escape", "quit_onboarding", "Exit Setup")]
    
    def __init__(self, step: int, total_steps: int, config_manager=None, flow=None, **kwargs):
        super().__init__(**kwargs)
        self.step = step
        self.total_steps = total_steps
        self.config_manager = config_manager
        self.flow = flow  # Reference to OnboardingFlow for state management
    
    def compose(self) -> ComposeResult:
        """Compose screen layout."""
        with Container():
            yield Label("", id="title", classes="title")
            yield Label("", id="progress", classes="progress")
            
            with Vertical(classes="content"):
                yield Label("", id="content")
            
            with Horizontal(classes="actions"):
                yield Button("Back", id="btn-back", variant="default")
                yield Button("Skip", id="btn-skip", variant="default")
                yield Button("Next", id="btn-next", variant="primary")
    
    def action_quit_onboarding(self) -> None:
        """Exit onboarding."""
        self.app.exit()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        button_id = event.button.id
        
        if button_id == "btn-back":
            if self.flow:
                self.flow.prev_screen()
            else:
                self.app.pop_screen()
        elif button_id == "btn-skip":
            # Skip remaining steps and mark complete
            if self.flow:
                self.flow.mark_complete()
            self.app.pop_screen()
        elif button_id == "btn-next":
            # Save state and move to next step
            self.save_step_state()
            if self.flow:
                self.flow.next_screen()
            else:
                self.app.pop_screen()
    
    def save_step_state(self) -> None:
        """Override in subclasses to save step data."""
        pass


class WelcomeScreen(OnboardingScreen):
    """Welcome and concept explanation."""
    
    def on_mount(self) -> None:
        title = self.query_one("#title", Label)
        progress = self.query_one("#progress", Label)
        content = self.query_one("#content", Label)
        
        title.update("[bold cyan]Welcome to Membria[/bold cyan]")
        progress.update(f"Step {self.step}/{self.total_steps}")
        
        welcome_text = """
[#FFB84D]Your Decision Intelligence Platform[/#FFB84D]

Membria captures your AI decisions, tracks outcomes, and
improves future choices through continuous calibration.

[#21C93A]What you'll build:[/#21C93A]
  ✓ A council of AI experts
  ✓ Decision memory graph
  ✓ Calibration system
  ✓ Context injection

[#5AA5FF]How it works:[/#5AA5FF]
  Decision → Code → Outcome → Calibration → Better Context

Let's set up your workspace!
"""
        content.update(welcome_text)


class ProviderSetupScreen(OnboardingScreen):
    """MCP front status (providers configured in MCP front)."""
    
    class ProviderSelected(Message):
        """Posted when provider is selected."""
        def __init__(self, provider: str):
            self.provider = provider
            super().__init__()
    
    def on_mount(self) -> None:
        title = self.query_one("#title", Label)
        progress = self.query_one("#progress", Label)
        title.update("[bold cyan]MCP Status[/bold cyan]")
        progress.update(f"Step {self.step}/{self.total_steps}")
        self._refresh_mcp_status()
    
    def compose(self) -> ComposeResult:
        """Show MCP front status."""
        with Container():
            yield Label("[bold cyan]MCP Status[/bold cyan]", id="title", classes="title")
            yield Label(f"Step {self.step}/{self.total_steps}", id="progress", classes="progress")
            
            with Vertical(classes="content"):
                yield Label(" ")
                yield Label("[#FFB84D]MCP Status:[/#FFB84D]")
                yield Label("[#5AA5FF]Managed by Membria (no setup required).[/#5AA5FF]")
                yield Label("[dim]Portal: {0}[/dim]".format(self._mcp_front_base()), id="mcp-portal")
                yield Label("[dim]Status: checking...[/dim]", id="mcp-status")
            
            with Horizontal(classes="actions"):
                yield Button("Back", id="btn-back")
                yield Button("Skip", id="btn-skip")
                yield Button("Open MCP Portal", id="btn-open-mcp-portal")
                yield Button("Refresh MCP", id="btn-refresh-mcp")
                yield Button("Next", id="btn-next", variant="primary")
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "btn-open-mcp-portal":
            webbrowser.open(f"{self._mcp_front_base()}/my/tokens")
            return
        if button_id == "btn-refresh-mcp":
            self._refresh_mcp_status()
            return
        await super().on_button_pressed(event)

    def _mcp_front_base(self) -> str:
        base = os.getenv("MEMBRIA_MCP_FRONT_URL", "").strip()
        if not base:
            base = "http://localhost:8080"
        return base.rstrip("/")

    def _refresh_mcp_status(self) -> None:
        status = self.query_one("#mcp-status", Label)
        base = self._mcp_front_base()
        status.update("[dim]Status: checking...[/dim]")
        import urllib.request
        import json

        def _check():
            try:
                with urllib.request.urlopen(f"{base}/health", timeout=2) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    return data.get("status") == "ok"
            except Exception:
                with urllib.request.urlopen(base, timeout=2) as resp:
                    return 200 <= resp.status < 300

        async def _run():
            try:
                ok = await asyncio.to_thread(_check)
                if ok:
                    status.update("[#21C93A]Status: reachable[/#21C93A]")
                else:
                    status.update("[#BF616A]Status: unavailable[/#BF616A]")
            except Exception:
                status.update("[#BF616A]Status: unreachable[/#BF616A]")

        self.call_later(_run)

    async def _handle_browser_login(self) -> None:
        status = self.query_one("#provider-status", Label)
        radio_set = self.query_one("#provider-select", RadioSet)
        provider = self._get_selected_provider(radio_set)
        if provider not in ("openai", "anthropic"):
            status.update("[#BF616A]✗ Browser login only for OpenAI or Anthropic[/#BF616A]")
            return
        status.update(f"[dim]Selected provider: {provider}[/dim]")
        oauth_input = self.query_one("#oauth-code-input", Input)
        code_value = oauth_input.value.strip()

        try:
            script = self._get_oauth_script(provider)
        except Exception:
            status.update("[#BF616A]✗ Browser login not supported for this provider[/#BF616A]")
            return

        if not code_value and provider == "openai":
            try:
                result = await asyncio.to_thread(self._run_oauth_script, script, ["--start"])
                url = result.get("url")
                verifier = result.get("verifier")
                if not url or not verifier:
                    status.update("[#BF616A]✗ OAuth start failed[/#BF616A]")
                    return
                self._oauth_verifier = verifier
                code_event, code_box, server = self._start_oauth_callback_server()
                self._oauth_server = server
                webbrowser.open(url)
                status.update("[#5AA5FF]Complete login in browser. Waiting for callback...[/#5AA5FF]")
                ok = await asyncio.to_thread(code_event.wait, 120)
                try:
                    server.shutdown()
                except Exception:
                    pass
                if not ok:
                    status.update("[#BF616A]✗ OAuth timed out. Try again.[/#BF616A]")
                    return
                code_value = code_box.get("code", "")
                if not code_value:
                    status.update("[#BF616A]✗ OAuth code not received.[/#BF616A]")
                    return
            except Exception:
                status.update("[#BF616A]✗ OAuth start error[/#BF616A]")
            return
        if not code_value and provider == "anthropic":
            try:
                result = await asyncio.to_thread(self._run_oauth_script, script, ["--start"])
                url = result.get("url")
                verifier = result.get("verifier")
                if not url or not verifier:
                    status.update("[#BF616A]✗ OAuth start failed[/#BF616A]")
                    return
                self._oauth_verifier = verifier
                webbrowser.open(url)
                status.update("[#5AA5FF]Open browser and paste redirect URL/code, then click Login again.[/#5AA5FF]")
            except Exception:
                status.update("[#BF616A]✗ OAuth start error[/#BF616A]")
            return

        verifier = getattr(self, "_oauth_verifier", "")
        if not verifier:
            status.update("[#BF616A]✗ Missing verifier. Click Login first.[/#BF616A]")
            return

        try:
            result = await asyncio.to_thread(
                self._run_oauth_script,
                script,
                ["--exchange", "--code", code_value, "--verifier", verifier],
            )
            if self.config_manager:
                self.config_manager.set(f"providers.{provider}.auth_method", "oauth")
                self.config_manager.set(f"providers.{provider}.auth_token", result.get("access", ""))
                self.config_manager.set(f"providers.{provider}.refresh_token", result.get("refresh", ""))
                self.config_manager.set(f"providers.{provider}.auth_expires", result.get("expires", 0))
                self.config_manager.set(f"providers.{provider}.enabled", True)
                self.config_manager.save()
            status.update("[#21C93A]✓ OAuth connected[/#21C93A]")
        except Exception as e:
            msg = str(e)
            try:
                Path("/tmp/membria_oauth_error.txt").write_text(msg)
            except Exception:
                pass
            if "token_exchange_failed:400" in msg:
                status.update("[#EBCB8B]⚠ Лимит исчерпан или доступ ограничен.[/#EBCB8B]")
            else:
                status.update("[#BF616A]✗ OAuth exchange error. See /tmp/membria_oauth_error.txt[/#BF616A]")

    def _start_oauth_callback_server(self):
        loop = asyncio.get_running_loop()
        code_event = threading.Event()
        code_box = {}

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urlparse(self.path)
                if parsed.path != "/auth/callback":
                    self.send_response(404)
                    self.end_headers()
                    return
                qs = parse_qs(parsed.query)
                code = (qs.get("code") or [""])[0]
                if code:
                    code_box["code"] = code
                    try:
                        loop.call_soon_threadsafe(code_event.set)
                    except Exception:
                        pass
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                if code:
                    html = f"""
                    <html>
                      <head>
                        <meta charset="utf-8" />
                        <title>Membria OAuth</title>
                        <style>
                          body {{ font-family: -apple-system, system-ui, sans-serif; padding: 24px; }}
                          .box {{ background: #f4f4f5; padding: 16px; border-radius: 8px; }}
                          code {{ display: block; white-space: pre-wrap; word-break: break-all; }}
                          button {{ margin-top: 12px; padding: 8px 12px; }}
                        </style>
                      </head>
                      <body>
                        <h3>Login complete</h3>
                        <p>Code captured. You can close this window.</p>
                        <div class="box">
                          <strong>Code:</strong>
                          <code id="code">{code}</code>
                          <button onclick="navigator.clipboard.writeText('{code}')">Copy code</button>
                        </div>
                      </body>
                    </html>
                    """
                else:
                    html = "<html><body><h3>No code received.</h3></body></html>"
                self.wfile.write(html.encode("utf-8"))

            def log_message(self, *_args):
                return

        server = HTTPServer(("127.0.0.1", 1455), Handler)

        def _serve():
            try:
                server.serve_forever()
            except Exception:
                pass

        loop.run_in_executor(None, _serve)
        return code_event, code_box, server

    def _get_oauth_script(self, provider: str) -> Path:
        base = Path(__file__).resolve().parent / "oauth"
        if provider == "openai":
            return base / "oauth_openai.mjs"
        if provider == "anthropic":
            return base / "oauth_anthropic.mjs"
        raise RuntimeError("unsupported")

    def _get_selected_provider(self, radio_set: RadioSet) -> str:
        button = radio_set.pressed_button
        if not button:
            try:
                for b in radio_set.query(RadioButton):
                    if getattr(b, "pressed", False):
                        button = b
                        break
            except Exception:
                button = None
        if not button:
            try:
                buttons = list(radio_set.query(RadioButton))
                button = buttons[0] if buttons else None
            except Exception:
                button = None
        if button:
            if button.id and button.id.startswith("opt-"):
                return button.id.replace("opt-", "")
            label = str(getattr(button, "label", "") or "").lower()
            if "openai" in label:
                return "openai"
            if "anthropic" in label or "claude" in label:
                return "anthropic"
            if "kilo" in label:
                return "kilo"
            if "ollama" in label:
                return "ollama"
            if "openrouter" in label:
                return "openrouter"
        return "anthropic"

    def _run_oauth_script(self, script: Path, args: list[str]) -> dict:
        cmd = ["node", str(script), *args]
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.strip() if e.stderr else ""
            stdout = e.stdout.strip() if e.stdout else ""
            msg = stderr or stdout or str(e)
            raise RuntimeError(msg) from e
        out = result.stdout.strip()
        return json.loads(out) if out else {}

    def save_step_state(self) -> None:
        """No-op: providers are configured in MCP front."""
        return


class RoleAssignmentScreen(OnboardingScreen):
    """Assign roles to providers."""
    
    def on_mount(self) -> None:
        title = self.query_one("#title", Label)
        progress = self.query_one("#progress", Label)
        title.update("[bold cyan]Role Assignment[/bold cyan]")
        progress.update(f"Step {self.step}/{self.total_steps}")
    
    def compose(self) -> ComposeResult:
        """Show role assignment options."""
        with Container():
            yield Label("[bold cyan]Role Assignment[/bold cyan]", id="title", classes="title")
            yield Label(f"Step {self.step}/{self.total_steps}", id="progress", classes="progress")
            
            with Vertical(classes="content"):
                yield Label("[#FFB84D]Build your expert council:[/#FFB84D]")
                
                # Role presets
                with RadioSet(id="role-preset"):
                    yield RadioButton("Full Power (Claude 3.5 + GPT-4)", value="full", id="opt-full")
                    yield RadioButton("Budget Friendly (Haiku + GPT-mini)", value="budget", id="opt-budget")
                    yield RadioButton("Local Only (Ollama)", value="local", id="opt-local")
                    yield RadioButton("Custom", value="custom", id="opt-custom")
            
            with Horizontal(classes="actions"):
                yield Button("Back", id="btn-back")
                yield Button("Skip", id="btn-skip")
                yield Button("Next", id="btn-next", variant="primary")
    
    def save_step_state(self) -> None:
        """Save role preset to config."""
        try:
            radio_set = self.query_one("#role-preset", RadioSet)
            preset = radio_set.pressed_button.value if radio_set.pressed_button else "full"
            
            if self.config_manager:
                self.config_manager.set("interactive.role_preset", preset)
                self.config_manager.save()
        except Exception:
            pass


class GraphDatabaseScreen(OnboardingScreen):
    """FalkorDB setup (optional)."""
    
    def on_mount(self) -> None:
        title = self.query_one("#title", Label)
        progress = self.query_one("#progress", Label)
        title.update("[bold cyan]Graph Database[/bold cyan]")
        progress.update(f"Step {self.step}/{self.total_steps}")
    
    def compose(self) -> ComposeResult:
        """Show FalkorDB setup options."""
        with Container():
            yield Label("[bold cyan]Graph Database[/bold cyan]", id="title", classes="title")
            yield Label(f"Step {self.step}/{self.total_steps}", id="progress", classes="progress")
            
            with Vertical(classes="content"):
                yield Label("[#FFB84D]Store your decision memory:[/#FFB84D]")
                
                with RadioSet(id="db-option"):
                    yield RadioButton("Docker (Recommended)", value="docker", id="opt-docker")
                    yield RadioButton("Binary", value="binary", id="opt-binary")
                    yield RadioButton("Managed Service", value="managed", id="opt-managed")
                    yield RadioButton("Skip (In-memory)", value="skip", id="opt-skip")
            
            with Horizontal(classes="actions"):
                yield Button("Back", id="btn-back")
                yield Button("Skip", id="btn-skip")
                yield Button("Next", id="btn-next", variant="primary")
    
    def save_step_state(self) -> None:
        """Save FalkorDB option to config."""
        try:
            radio_set = self.query_one("#db-option", RadioSet)
            db_mode = radio_set.pressed_button.value if radio_set.pressed_button else "skip"
            
            if self.config_manager:
                self.config_manager.set("falkordb.mode", db_mode)
                self.config_manager.save()
        except Exception:
            pass


class MonitoringLevelScreen(OnboardingScreen):
    """Choose monitoring/logging level."""
    
    def on_mount(self) -> None:
        title = self.query_one("#title", Label)
        progress = self.query_one("#progress", Label)
        title.update("[bold cyan]Monitoring Level[/bold cyan]")
        progress.update(f"Step {self.step}/{self.total_steps}")
    
    def compose(self) -> ComposeResult:
        """Show monitoring level options."""
        with Container():
            yield Label("[bold cyan]Monitoring Level[/bold cyan]", id="title", classes="title")
            yield Label(f"Step {self.step}/{self.total_steps}", id="progress", classes="progress")
            
            with Vertical(classes="content"):
                yield Label("[#FFB84D]How verbose should logging be?[/#FFB84D]")
                
                with RadioSet(id="monitor-level"):
                    yield RadioButton("🤐 L0: Silent (production)", value="L0", id="opt-l0")
                    yield RadioButton("📝 L1: Decisions (default)", value="L1", id="opt-l1")
                    yield RadioButton("🧠 L2: Reasoning", value="L2", id="opt-l2")
                    yield RadioButton("🔍 L3: Debug (verbose)", value="L3", id="opt-l3")
            
            with Horizontal(classes="actions"):
                yield Button("Back", id="btn-back")
                yield Button("Skip", id="btn-skip")
                yield Button("Next", id="btn-next", variant="primary")
    
    def save_step_state(self) -> None:
        """Save monitoring level to config."""
        try:
            radio_set = self.query_one("#monitor-level", RadioSet)
            level = radio_set.pressed_button.value if radio_set.pressed_button else "L1"
            
            if self.config_manager:
                self.config_manager.set("monitoring.level", level)
                self.config_manager.save()
        except Exception:
            pass


class ThemeSelectionScreen(OnboardingScreen):
    """Choose color theme."""
    
    def on_mount(self) -> None:
        title = self.query_one("#title", Label)
        progress = self.query_one("#progress", Label)
        title.update("[bold cyan]Color Theme[/bold cyan]")
        progress.update(f"Step {self.step}/{self.total_steps}")
    
    def compose(self) -> ComposeResult:
        """Show theme options."""
        with Container():
            yield Label("[bold cyan]Color Theme[/bold cyan]", id="title", classes="title")
            yield Label(f"Step {self.step}/{self.total_steps}", id="progress", classes="progress")
            
            with Vertical(classes="content"):
                yield Label("[#FFB84D]Personalize your CLI:[/#FFB84D]")
                
                with RadioSet(id="theme-select"):
                    themes = [
                        ("nord", "Arctic palette"),
                        ("gruvbox", "Retro groove"),
                        ("tokyo-night", "Cyberpunk"),
                        ("solarized-light", "Light mode"),
                        ("solarized-dark", "Dark mode"),
                        ("dracula", "Vampire theme"),
                        ("one-dark", "Atom-like"),
                        ("monokai", "High contrast"),
                    ]
                    
                    for theme_name, desc in themes:
                        yield RadioButton(f"  {theme_name.replace('-', ' ').title()}", 
                                        value=theme_name, 
                                        id=f"opt-{theme_name}")
            
            with Horizontal(classes="actions"):
                yield Button("Back", id="btn-back")
                yield Button("Skip", id="btn-skip")
                yield Button("Next", id="btn-next", variant="primary")
    
    def save_step_state(self) -> None:
        """Save theme selection to config."""
        try:
            radio_set = self.query_one("#theme-select", RadioSet)
            theme = radio_set.pressed_button.value if radio_set.pressed_button else "nord"
            
            if self.config_manager:
                self.config_manager.set("display.theme", theme)
                self.config_manager.save()
        except Exception:
            pass


class FirstDecisionScreen(OnboardingScreen):
    """Capture first decision (tutorial)."""
    
    def on_mount(self) -> None:
        title = self.query_one("#title", Label)
        progress = self.query_one("#progress", Label)
        title.update("[bold cyan]First Decision[/bold cyan]")
        progress.update(f"Step {self.step}/{self.total_steps}")
    
    def compose(self) -> ComposeResult:
        """Show decision capture form."""
        with Container():
            yield Label("[bold cyan]First Decision[/bold cyan]", id="title", classes="title")
            yield Label(f"Step {self.step}/{self.total_steps}", id="progress", classes="progress")
            
            with Vertical(classes="content"):
                yield Label("[#FFB84D]Experience Membria in action[/#FFB84D]")
                yield Label("")
                yield Label("Your decision:")
                yield Input(id="decision-statement", placeholder="e.g., Use JWT for authentication")
                yield Label("")
                yield Label("How confident? (0-100):")
                yield Input(id="decision-confidence", placeholder="80")
                yield Label("")
                yield Label("Domain:")
                yield Input(id="decision-domain", placeholder="architecture, database, auth, etc")
            
            with Horizontal(classes="actions"):
                yield Button("Back", id="btn-back")
                yield Button("Skip", id="btn-skip")
                yield Button("Finish", id="btn-finish", variant="primary")
    
    def save_step_state(self) -> None:
        """Save first decision to config."""
        try:
            decision = self.query_one("#decision-statement", Input).value
            confidence = self.query_one("#decision-confidence", Input).value
            domain = self.query_one("#decision-domain", Input).value
            
            if self.config_manager and decision:
                self.config_manager.set("first_decision", {
                    "statement": decision,
                    "confidence": int(confidence) if confidence.isdigit() else 50,
                    "domain": domain,
                })
                self.config_manager.save()
        except Exception:
            pass
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks with special handling for Finish."""
        button_id = event.button.id
        
        if button_id == "btn-finish":
            # Save state and finish onboarding
            self.save_step_state()
            if self.flow:
                self.flow.mark_complete()
            self.app.pop_screen()
        else:
            # Use parent handler
            super().on_button_pressed(event)


class SummaryScreen(OnboardingScreen):
    """Setup summary and completion."""
    
    def on_mount(self) -> None:
        title = self.query_one("#title", Label)
        progress = self.query_one("#progress", Label)
        title.update("[bold cyan]Setup Complete![/bold cyan]")
        progress.update(f"Step {self.total_steps}/{self.total_steps}")
    
    def compose(self) -> ComposeResult:
        """Show setup summary."""
        with Container():
            yield Label("[bold cyan]Setup Complete![/bold cyan]", id="title", classes="title")
            yield Label(f"Step {self.total_steps}/{self.total_steps}", id="progress", classes="progress")
            
            with Vertical(classes="content"):
                yield Label("[#21C93A]✅ You've configured:[/#21C93A]")
                yield Label("")
                yield Label("📦 Providers: Anthropic, OpenAI")
                yield Label("👥 Roles: Architect, Security, Database, Moderator")
                yield Label("🗄️  Graph Database: Docker")
                yield Label("📊 Monitoring: L1 (Decisions)")
                yield Label("🎨 Theme: nord")
                yield Label("📝 First Decision: Recorded")
                yield Label("")
                yield Label("[#E8E8E8]Next steps:[/#E8E8E8]")
                yield Label("  1. Type /help for all commands")
                yield Label("  2. Use /plan to start delegating")
                yield Label("  3. Check /settings to adjust config")
            
            with Horizontal(classes="actions"):
                yield Button("Back", id="btn-back")
                yield Button("Start!", id="btn-start", variant="primary")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        button_id = event.button.id
        
        if button_id == "btn-start":
            # Mark onboarding complete and exit
            if self.flow:
                self.flow.mark_complete()
            self.app.pop_screen()
        else:
            super().on_button_pressed(event)


class OnboardingFlow:
    """Manages the sequence of onboarding screens."""
    
    def __init__(self, app, config_manager):
        self.app = app
        self.config_manager = config_manager
        self.current_step = 0
        self.completed = False
        self.screens = [
            WelcomeScreen,
            ProviderSetupScreen,
            RoleAssignmentScreen,
            GraphDatabaseScreen,
            MonitoringLevelScreen,
            ThemeSelectionScreen,
            FirstDecisionScreen,
            SummaryScreen,
        ]
    
    def start(self):
        """Start the onboarding flow."""
        self.show_screen(0)
    
    def show_screen(self, step: int):
        """Show a specific onboarding screen."""
        if 0 <= step < len(self.screens):
            screen_class = self.screens[step]
            screen = screen_class(
                step=step+1,
                total_steps=len(self.screens),
                config_manager=self.config_manager,
                flow=self
            )
            self.app.push_screen(screen)
    
    def next_screen(self):
        """Go to next screen."""
        self.current_step += 1
        if self.current_step < len(self.screens):
            self.show_screen(self.current_step)
        else:
            self.mark_complete()
    
    def prev_screen(self):
        """Go to previous screen."""
        if self.current_step > 0:
            self.current_step -= 1
            self.show_screen(self.current_step)
    
    def mark_complete(self):
        """Mark onboarding as complete and remove all screens."""
        self.completed = True
        # Mark in config that onboarding is done
        try:
            self.config_manager.set("onboarding.completed", True)
            self.config_manager.save()
        except Exception:
            pass
        
        # Pop all onboarding screens
        try:
            while len(self.app.screen_stack) > 1:
                self.app.pop_screen()
        except Exception:
            pass
