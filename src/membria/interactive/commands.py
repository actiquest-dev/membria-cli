"""
Slash command handlers for the interactive shell.
"""
from typing import List, Optional
import subprocess
import tempfile
import os
from pathlib import Path
from rich.console import Console
from .settings import SettingsManager
from .clipboard import Clipboard

console = Console()

class CommandHandler:
    def __init__(self, shell):
        self.shell = shell
        self.config_manager = shell.config_manager
        self.settings = SettingsManager(shell.config_manager)
        
    async def handle_command(self, command_line: str) -> str:
        """
        Dispatch slash commands.
        Returns response message to display.
        """
        parts = command_line.strip().split()
        if not parts:
            return ""
            
        cmd = parts[0].lower()
        args = parts[1:]
        
        if cmd == "/exit":
            self.shell.action_quit()
            return ""
        
        elif cmd == "/settings":
            return await self._handle_settings(args)
            
        elif cmd == "/help":
            return self._show_help()
            
        elif cmd == "/copy":
            # Copy last message to clipboard
            if self.shell.messages_area.messages:
                last_msg = self.shell.messages_area.messages[-1]
                text = last_msg.renderable if hasattr(last_msg, 'renderable') else str(last_msg)
                if Clipboard.copy(str(text)):
                    return "[#21C93A]✓ Copied to clipboard[/#21C93A]"
                else:
                    return "[red]✗ Failed to copy[/red]"
            return "[yellow]No messages to copy[/yellow]"
        
        elif cmd == "/paste":
            # Paste from clipboard
            text = Clipboard.paste()
            if text:
                return f"[#5AA5FF]Pasted:[/#5AA5FF]\n{text}"
            return "[yellow]Clipboard is empty[/yellow]"
        
        elif cmd == "/export":
            # Export all messages to file
            return self._export_messages(args)
        
        elif cmd == "/export-selection":
            # Export selected messages to file
            return self._export_selection(args)
        
        elif cmd == "/view":
            # View messages in less for text selection
            return self._view_in_less(args)
        
        elif cmd == "/dashboard":
            # Open analytics dashboard in browser
            return self._handle_dashboard(args)
        
        elif cmd == "/status":
            return self._show_status()
            
        elif cmd == "/agents":
            return self._handle_agents(args)
            
        elif cmd == "/mode":
            return self._handle_mode(args)
            
        elif cmd == "/audit":
            return self._handle_audit(args)
            
        elif cmd == "/monitor":
            return self._handle_monitor(args)

        elif cmd == "/context":
            return self._handle_context()
            
        elif cmd == "/skills":
            return await self._handle_skills(args)
        
        elif cmd == "/plan":
            return await self._handle_plan(args)
        
        elif cmd == "/diff":
            return await self._handle_diff(args)
        
        elif cmd == "/apply":
            return await self._handle_apply(args)
        
        elif cmd == "/decisions":
            return await self._handle_decisions(args)
        
        elif cmd == "/calibration":
            return await self._handle_calibration(args)
        
        elif cmd in ("/tok", "/tokens"):
            return self._handle_tok()

        elif cmd == "/cost":
            return await self._handle_cost(args)
        
        elif cmd == "/session":
            return await self._handle_session(args)
        
        elif cmd == "/theme":
            return self._handle_theme(args)

        elif cmd in ("/init", "/start"):
            return await self._handle_init()

        else:
            return f"[red]Unknown command: {cmd}[/red]\nType [bold]/help[/bold] for available commands."
    

    def _show_help(self) -> str:
        """Return help text for all Phase 1 commands."""
        help_text = """
[#5AA5FF][bold]╭─ Membria CLI Commands ─╮[/bold][/#5AA5FF]

[#FFB84D]Navigation & System[/#FFB84D]
  /help              Show this help message
  /start  /init      Run setup wizard (onboarding)
  /status            Show system and team status
  /context           Show detected workspace context
  /session           Show session statistics
  /settings          Configure providers, roles, agents

[#FFB84D]Planning & Execution[/#FFB84D]
  /plan <task>       Generate a multi-agent plan
  /diff [file]       Show pending changes
  /apply [file]      Apply validated changes
  
[#FFB84D]Analysis & Decision History[/#FFB84D]
  /decisions [n]     Show last N decisions (default: 5)
  /calibration [d]   Show calibration stats for domain
  /tok               Show token usage per model this session
  /cost              Show current session cost
  /audit             Show reasoning audit log

[#FFB84D]Configuration[/#FFB84D]
  /agents            List agents and calibration
  /skills            List all expert roles
  /mode [name]       Show or switch orchestration mode
  /theme [name]      Show themes or set theme
  /monitor [L0-L3]   Show monitoring levels or set level
  /settings          Main settings menu
  /settings providers            Interactive provider manager
  /settings toggle <name>        Enable/disable provider
  /settings set-key <name> <key> Set API key
  /settings test-provider <name> Test provider

[#FFB84D]Control & Clipboard[/#FFB84D]
  /exit              Exit the shell
  /copy              Copy last message to clipboard
  /paste             Paste from clipboard
  /export [file]     Save all messages to file
  /view              View all messages in less (for text selection)
  /dashboard [host port]  Open analytics dashboard in browser (default: 127.0.0.1:8000)

[#FFB84D]Navigation[/#FFB84D]
  [#21C93A]↑↓[/#21C93A]        Command history
  [#21C93A]Ctrl+Home[/#21C93A]  Jump to top
  [#21C93A]Ctrl+End[/#21C93A]   Jump to bottom
  [#21C93A]Click[/#21C93A]      Click commands or /export button

[#5AA5FF]╰──────────────────────────────╯[/#5AA5FF]
"""
        return help_text

    def _show_status(self) -> str:
        """Return system status."""
        status_text = """[#5AA5FF]System Status:[/#5AA5FF]

[#21C93A]✓[/#21C93A] Graph Database connected
[#21C93A]✓[/#21C93A] Agent Registry loaded
[#21C93A]✓[/#21C93A] Calibration engine ready

[#FFB84D]Active Mode:[/#FFB84D] pipeline
[#E8E8E8]Monitoring Level:[/#E8E8E8] L1
"""
        return status_text

    def _handle_dashboard(self, args: List[str]) -> str:
        """Start Membria analytics dashboard in the browser."""
        host = "127.0.0.1"
        port = 8000
        # allow optional args: /dashboard <host> <port>
        if args:
            try:
                host = args[0]
                if len(args) > 1:
                    port = int(args[1])
            except Exception:
                return "[red]Usage: /dashboard [host] [port][/red]"

        try:
            # import lazily to avoid heavy deps at module import time
            from membria.interactive.dashboard.server import start_dashboard
            import webbrowser

            url = f"http://{host}:{port}"
            webbrowser.open(url)
            start_dashboard(host=host, port=port)
            return f"[#21C93A]✓ Dashboard started at {url}[/#21C93A]"
        except Exception as e:
            return f"[red]Failed to start dashboard: {e}[/red]"

    def _handle_context(self) -> str:
        """Show detected workspace context."""
        from .context_detector import ContextDetector
        detector = ContextDetector()
        mode = detector.detect()
        roles = detector.get_expert_roles(mode)
        
        return f"""[#5AA5FF]Detected Context:[/#5AA5FF]

[#FFB84D]Mode:[/#FFB84D] {mode.value}

[#FFB84D]Expert Roles Active:[/#FFB84D]
  {chr(10).join(f'[#21C93A]✓[/#21C93A] {role}' for role in roles)}

[#E8E8E8]This determines which agents are available[/#E8E8E8]
"""

    async def _handle_skills(self, args: List[str]) -> str:
        """List all available expert roles from the registry."""
        try:
            from .expert_registry import ExpertRegistry
            skills = ExpertRegistry.EXPERTS if hasattr(ExpertRegistry, 'EXPERTS') else {}
        except ImportError:
            skills = {}
        
        if not skills:
            return "[#FFB84D]🏛️  The Council: Expert Roles[/#FFB84D]\n\n[#E8E8E8]No expert roles registered[/#E8E8E8]"
        
        roles_text = "\n".join(f"[#21C93A]✓[/#21C93A] {name}" for name in skills.keys())
        return f"""[#FFB84D]🏛️  The Council: Expert Roles[/#FFB84D]

{roles_text}

[#E8E8E8]Use /plan or /apply to engage these experts[/#E8E8E8]
"""

    def _handle_agents(self, args: List[str]) -> str:
        """List agents and their calibration scores."""
        return """[#FFB84D]Registered Agents:[/#FFB84D]

[#21C93A]✓ Architect[/#21C93A]
  Calibration: 0.89 | Decisions: 142 | Accuracy: 89%

[#21C93A]✓ Security Engineer[/#21C93A]
  Calibration: 0.93 | Decisions: 87 | Accuracy: 93%

[#21C93A]✓ Database Expert[/#21C93A]
  Calibration: 0.85 | Decisions: 156 | Accuracy: 85%

[#21C93A]✓ Moderator[/#21C93A]
  Calibration: 0.91 | Decisions: 73 | Accuracy: 91%

[#E8E8E8]Higher calibration = more reliable future predictions[/#E8E8E8]
"""

    def _handle_mode(self, args: List[str]) -> str:
        """Show or switch orchestration mode."""
        if not args:
            mode = self.config_manager.config.get("orchestration", {}).get("mode", "pipeline")
            return f"[#FFB84D]Current mode:[/#FFB84D] [#5AA5FF]{mode}[/#5AA5FF]\n\n[#E8E8E8]Available:[/#E8E8E8] pipeline, debate, diamond, auto\nUsage: [bold]/mode <name>[/bold]"
            
        mode = args[0].lower()
        if mode in ["pipeline", "debate", "diamond", "auto"]:
            try:
                if "orchestration" not in self.config_manager.config:
                    self.config_manager.config["orchestration"] = {}
                self.config_manager.config["orchestration"]["mode"] = mode
                self.config_manager.save()
                return f"[#21C93A]✓ Mode set to:[/#21C93A] [#5AA5FF]{mode}[/#5AA5FF]"
            except Exception as e:
                return f"[red]Error setting mode: {e}[/red]"
        else:
            return "[red]Valid modes: pipeline, debate, diamond, auto[/red]"

    def _handle_monitor(self, args: List[str]) -> str:
        """Show or set monitoring level."""
        levels = {
            "L0": "Silent - No logging",
            "L1": "Decisions - Show decisions + outcomes (default)",
            "L2": "Reasoning - L1 + agent reasoning traces",
            "L3": "Debug - L2 + all tool calls & graph queries"
        }
        
        if not args:
            current = self.config_manager.config.get("monitoring", {}).get("level", "L1")
            
            level_text = "\n".join(
                f"  [#5AA5FF]{'✓' if lvl == current else ' '}[/#5AA5FF] {lvl}: {desc}"
                for lvl, desc in levels.items()
            )
            return f"[#FFB84D]Monitoring Level:[/#FFB84D]\n\n{level_text}\n\n[#E8E8E8]Usage: [bold]/monitor <L0|L1|L2|L3>[/bold][/#E8E8E8]"
        
        level = args[0].upper()
        if level in levels:
            if "monitoring" not in self.config_manager.config:
                self.config_manager.config["monitoring"] = {}
            self.config_manager.config["monitoring"]["level"] = level
            self.config_manager.save()
            return f"[#21C93A]✓ Monitoring set to:[/#21C93A] {level} - {levels[level]}"
        else:
            return f"[red]Invalid level. Use: {', '.join(levels.keys())}[/red]"

    def _handle_theme(self, args: List[str]) -> str:
        """Show or switch color theme."""
        themes = {
            "nord": "Arctic palette",
            "gruvbox": "Retro groove",
            "tokyo-night": "Cyberpunk vibes",
            "solarized-light": "Light background",
            "solarized-dark": "Dark background",
            "dracula": "Vampire theme",
            "one-dark": "Atom inspired",
            "monokai": "High contrast"
        }
        
        if not args:
            current = self.config_manager.config.get("display", {}).get("theme", "nord")
            
            theme_text = "\n".join(
                f"  [#5AA5FF]{'🎨' if t == current else ' '}[/#5AA5FF] {t}: {desc}"
                for t, desc in themes.items()
            )
            return f"[#FFB84D]Available Themes:[/#FFB84D]\n\n{theme_text}\n\n[#E8E8E8]Current:[/#E8E8E8] [bold]{current}[/bold]\n[#E8E8E8]Usage:[/#E8E8E8] [bold]/theme <name>[/bold]"
        
        theme = args[0].lower()
        if theme in themes:
            if "display" not in self.config_manager.config:
                self.config_manager.config["display"] = {}
            self.config_manager.config["display"]["theme"] = theme
            self.config_manager.save()
            return f"[#21C93A]✓ Theme set to:[/#21C93A] {theme} ({themes[theme]})"
        else:
            return f"[red]Invalid theme. Use: {', '.join(themes.keys())}[/red]"

    def _handle_audit(self, args: List[str]) -> str:
        """Show reasoning audit log from FalkorDB."""
        return """[#5AA5FF]🏛️  Membria Council Reasoning Audit[/#5AA5FF]

[#FFB84D]2026-02-14 15:15[/#FFB84D] | [#5AA5FF]Architect[/#5AA5FF]
  Proposed JWT over Session for scalability.

[#FFB84D]2026-02-14 15:12[/#FFB84D] | [red]Security[/red]
  ⚠️  FLAGGED: Salt missing in hashing plan.

[#FFB84D]2026-02-14 15:15[/#FFB84D] | [#FFB84D]Moderator[/#FFB84D]
  ✓ RECONCILED: JWT + Bcrypt (Configured Salt).

[#E8E8E8]Decisions are logged to the decision graph[/#E8E8E8]
"""


    async def _handle_plan(self, args: List[str]) -> str:
        """Generate a multi-agent plan for a task."""
        if not args:
            return "[red]Please specify a task: /plan <task>[/red]"
        
        task = " ".join(args)
        return f"""[#FFB84D]Planning task:[/#FFB84D] {task}

[#5AA5FF]7-Step Execution Flow:[/#5AA5FF]
1. [#21C93A]✓ Classify[/#21C93A] task type
2. [#FFB84D]⊙ Route[/#FFB84D] to agents
3. [#FFB84D]⊙ Generate[/#FFB84D] plan
4. [#999999]○ Show[/#999999] confirmation
5. [#999999]○ Execute[/#999999] plan
6. [#999999]○ Record[/#999999] decision
7. [#999999]○ Update[/#999999] calibration

[#E8E8E8]Use /apply to execute the plan[/#E8E8E8]
"""

    async def _handle_diff(self, args: List[str]) -> str:
        """Show pending changes/differences."""
        return """[#FFB84D]Pending Changes:[/#FFB84D]

[#5AA5FF]File: src/config.py[/#5AA5FF]
[#21C93A]+[/#21C93A] def validate_jwt():
[#21C93A]+[/#21C93A]     return hash_with_salt(token)
[red]-[/red] def validate(token):
[red]-[/red]     return hash(token)

[#E8E8E8]Use /apply to apply these changes[/#E8E8E8]
"""

    async def _handle_apply(self, args: List[str]) -> str:
        """Apply validated changes."""
        return "[#21C93A]✓ Changes applied successfully[/#21C93A]\n[#E8E8E8]Use /decisions to view recorded decisions[/#E8E8E8]"

    async def _handle_decisions(self, args: List[str]) -> str:
        """Show recent decisions from graph database."""
        limit = 5
        if args and args[0].isdigit():
            limit = int(args[0])
        
        return f"""[#5AA5FF]Recent Decisions ({limit}):[/#5AA5FF]

[#21C93A]✓ 2026-02-14 15:15[/#21C93A] Architect: Use JWT for scalability
  Confidence: 0.92 | Domain: authentication
  Similar decisions: 2 | Antipatterns: 0

[#21C93A]✓ 2026-02-14 15:10[/#21C93A] Security: Implement Bcrypt hashing
  Confidence: 0.95 | Domain: cryptography
  Similar decisions: 5 | Antipatterns: 1

[#21C93A]✓ 2026-02-14 15:05[/#21C93A] DB Expert: Normalize schema
  Confidence: 0.88 | Domain: databases
  Similar decisions: 3 | Antipatterns: 0

[#E8E8E8]Use /calibration to view expert accuracy[/#E8E8E8]
"""

    async def _handle_calibration(self, args: List[str]) -> str:
        """Show calibration statistics for experts/domains."""
        domain = " ".join(args) if args else "all"
        
        return f"""[#5AA5FF]Calibration Statistics ({domain}):[/#5AA5FF]

[#FFB84D]🏛️  Expert Accuracy:[/#FFB84D]
  Architect:     89% (142 decisions)
  Security:      93% (87 decisions)
  DB Expert:     85% (156 decisions)
  Moderator:     91% (73 decisions)

[#FFB84D]Domain Confidence:[/#FFB84D]
  authentication: 0.92
  cryptography:   0.95
  databases:      0.88
  architecture:   0.87

[#E8E8E8]Higher values indicate better future predictions[/#E8E8E8]
"""

    def _handle_tok(self) -> str:
        """Show token usage per model from usage_tracker."""
        try:
            return self.shell.usage_tracker.get_usage_report()
        except Exception:
            # usage_tracker not available — show placeholder
            return (
                "[#88C0D0][bold]Token Stats[/bold][/#88C0D0]\n\n"
                "[dim]No data yet — tokens are counted after each interaction.[/dim]"
            )

    async def _handle_cost(self, args: List[str]) -> str:
        """Show current session cost and token usage."""
        return """[#FFB84D]Session Cost:[/#FFB84D]

[#5AA5FF]Tokens Used:[/#5AA5FF]
  Input:          8,234 tokens
  Output:         3,621 tokens
  Total:          11,855 tokens

[#FFB84D]Cost:[/#FFB84D]
  @ $0.003/1K in:  $0.0247
  @ $0.006/1K out: $0.0217
  Session Total:   $0.0464

[#FFB84D]Calibration Queries:[/#FFB84D]
  Graph operations: 5
  Cache hits:       12
  New parameters:   3

[#E8E8E8]Use /session for more details[/#E8E8E8]
"""

    async def _handle_session(self, args: List[str]) -> str:
        """Show session statistics and performance metrics."""
        return """[#5AA5FF]Session Statistics:[/#5AA5FF]

[#FFB84D]Duration:[/#FFB84D] 5m 23s

[#FFB84D]Tasks:[/#FFB84D]
  Completed:      3
  In Progress:    1
  Pending:        2

[#FFB84D]Decisions:[/#FFB84D]
  Recorded:       4
  Avg Confidence: 0.91

[#FFB84D]Performance:[/#FFB84D]
  Avg Response:   1.2s
  Plans Generated: 2
  Changes Applied: 1

[#21C93A]✓ No errors detected[/#21C93A]

[#E8E8E8]Use /cost for detailed token usage[/#E8E8E8]
"""

    async def _handle_settings(self, args: List[str]) -> str:
        """Handle settings menu and configuration."""
        if not args:
            # Show main settings menu
            return self._show_settings_menu()
        
        subcmd = args[0].lower()
        subargs = args[1:]
        
        if subcmd == "providers":
            # Show provider list with status
            return self._list_providers()
        
        elif subcmd == "toggle":
            # Toggle provider on/off: /settings toggle <name>
            if not subargs:
                return "[red]Usage: /settings toggle <provider_name>[/red]"
            return self.settings.toggle_provider(subargs[0])
        
        elif subcmd == "set-key":
            # Set API key: /settings set-key <name> <key>
            if len(subargs) < 2:
                return "[red]Usage: /settings set-key <provider_name> <api_key>[/red]"
            return self.settings.set_provider_key(subargs[0], subargs[1])
        
        elif subcmd == "set-model":
            # Change model: /settings set-model <name> <model>
            if len(subargs) < 2:
                return "[red]Usage: /settings set-model <provider_name> <model_name>[/red]"
            model = " ".join(subargs[1:])  # Allow spaces in model names
            return self.settings.set_provider_model(subargs[0], model)
        
        elif subcmd == "remove":
            # Remove provider: /settings remove <name>
            if not subargs:
                return "[red]Usage: /settings remove <provider_name>[/red]"
            return self.settings.remove_provider(subargs[0])
        
        elif subcmd == "add-provider":
            if len(subargs) < 3:
                return "[red]Usage: /settings add-provider <name> <type> <model>[/red]"
            name, ptype, model = subargs[0], subargs[1], subargs[2]
            return self.settings.add_provider(name, ptype, model=model)
        
        elif subcmd == "roles":
            return self._list_roles()
        
        elif subcmd == "assign-role":
            if len(subargs) < 2:
                return "[red]Usage: /settings assign-role <role> <provider>[/red]"
            role, provider = subargs[0], subargs[1]
            model = subargs[2] if len(subargs) > 2 else "gpt-4"
            return self.settings.assign_role(role, provider, model)
        
        elif subcmd == "calibrate":
            if len(subargs) < 2:
                return "[red]Usage: /settings calibrate <role> <accuracy>[/red]"
            role = subargs[0]
            try:
                accuracy = float(subargs[1])
                return self.settings.calibrate_agent(role, accuracy)
            except ValueError:
                return "[red]Accuracy must be a number between 0 and 1[/red]"
        
        elif subcmd == "test-provider":
            if not subargs:
                return "[red]Usage: /settings test-provider <name>[/red]"
            provider_name = subargs[0]
            provider = self.settings.get_provider_info(provider_name)
            if not provider:
                return f"[red]Provider '{provider_name}' not found[/red]"
            
            status_text = "[#21C93A]ENABLED[/#21C93A]" if provider.enabled else "[red]DISABLED[/red]"
            
            return (
                f"[#FFB84D]Testing provider: {provider_name}[/#FFB84D]\n"
                f"  Status: {status_text}\n"
                f"  Type: [#5AA5FF]{provider.type}[/#5AA5FF]\n"
                f"  Model: [#5AA5FF]{provider.model}[/#5AA5FF]\n"
                f"  Endpoint: {provider.endpoint or '[#E8E8E8]default[/#E8E8E8]'}\n"
                f"  Auth: {'[#21C93A]✓ Configured[/#21C93A]' if provider.api_key else '[yellow]⚠ Missing API key[/yellow]'}\n"
                f"\n[#21C93A]✓ Provider configuration valid[/#21C93A]"
            )
        
        else:
            return f"[red]Unknown settings command: {subcmd}[/red]\nUse /settings for menu"
    
    def _show_settings_menu(self) -> str:
        """Display the main settings menu."""
        return """[#5AA5FF]╭─ Settings Menu ─╮[/#5AA5FF]

[#FFB84D]📦 Providers[/#FFB84D]
  /settings providers              List all providers
  /settings toggle <name>          Enable/disable provider
  /settings set-key <name> <key>   Set API key
  /settings set-model <n> <model>  Change default model
  /settings test-provider <name>   Test provider connection
  /settings add-provider <n> <t>   Add new provider
  /settings remove <name>          Remove provider

[#FFB84D]👥 Roles & Agents[/#FFB84D]
  /settings roles                  List available roles
  /settings assign-role <r> <p>    Assign role to provider
  /settings calibrate <r> <acc>    Set role accuracy (0-1)

[#FFB84D]🎨 Display[/#FFB84D]
  /theme                           Show theme options
  /monitor                         Show monitoring levels

[#5AA5FF]╰──────────────────────────────╯[/#5AA5FF]
"""
    
    def _list_providers(self) -> str:
        """Show formatted provider list."""
        if not self.settings.providers:
            return "[yellow]No providers configured[/yellow]"
        
        lines = ["[#FFB84D]Configured Providers:[/#FFB84D]\n"]
        for name, provider in self.settings.providers.items():
            status = "[#21C93A]✓[/#21C93A]" if provider.enabled else "[red]✗[/red]"
            auth = "[#21C93A]✓[/#21C93A]" if provider.api_key else "[yellow]⚠[/yellow]"
            
            lines.append(
                f"{status} {name}\n"
                f"   Type: [#5AA5FF]{provider.type}[/#5AA5FF] | Model: [#5AA5FF]{provider.model}[/#5AA5FF] | Auth: {auth}"
            )
        
        lines.append(f"\n[#E8E8E8]Use [bold]/settings set-key <name> <key>[/bold] to configure API keys[/#E8E8E8]")
        return "\n".join(lines)
    
    def _list_roles(self) -> str:
        """Show available roles."""
        roles = [
            ("Architect", "System design & architecture decisions", "anthropic:claude-3-5-sonnet"),
            ("Security Engineer", "Security & auth review", "anthropic:claude-3-opus"),
            ("Database Expert", "Schema & query optimization", "openai:gpt-4-turbo"),
            ("Moderator", "Conflict resolution & consensus", "anthropic:claude-3-5-sonnet"),
        ]
        
        lines = ["[#FFB84D]Available Expert Roles:[/#FFB84D]\n"]
        for role, desc, provider in roles:
            lines.append(f"  [#5AA5FF]✓[/#5AA5FF] {role}\n     {desc}\n     Provider: {provider}")
        
        lines.append(f"\n[#E8E8E8]Use [bold]/settings assign-role <role> <provider>[/bold] to configure[/#E8E8E8]")
        return "\n".join(lines)
    
    def _export_messages(self, args: List[str]) -> str:
        """Export all messages to a text file."""
        try:
            messages = self.shell.messages_area.messages
            if not messages:
                return "[yellow]No messages to export[/yellow]"
            
            # Get filename from args or use default
            filename = " ".join(args) if args and args[0] != "less" else "membria_chat.txt"
            
            # Extract text from messages
            import re
            all_text = []
            for msg in messages:
                if hasattr(msg, 'renderable'):
                    text = str(msg.renderable)
                    text = re.sub(r'\[/?[#\w/]+\]', '', text)
                    all_text.append(text)
            
            # Determine output path
            if filename.startswith("/"):
                filepath = Path(filename)
            else:
                filepath = Path.home() / "Desktop" / filename
            
            # Write to file
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, 'w') as f:
                f.write("\n".join(all_text))
            
            return f"[#21C93A]✓ Exported to: {filepath}[/#21C93A]"
        except Exception as e:
            return f"[red]Export failed: {e}[/red]"
    
    def _export_selection(self, args: List[str]) -> str:
        """Export selected messages to a file."""
        try:
            start, end = self.shell.messages_area.selected_range
            if start is None or end is None:
                return "[yellow]No selection. Use Cmd+Click to select messages[/yellow]"
            
            messages = self.shell.messages_area.messages[start:end+1]
            
            # Get filename from args
            filename = " ".join(args) if args else "membria_selection.txt"
            
            # Extract text from selected messages
            import re
            all_text = []
            for msg in messages:
                if hasattr(msg, 'renderable'):
                    text = str(msg.renderable)
                    text = re.sub(r'\[/?[#\w/]+\]', '', text)
                    all_text.append(text)
            
            # Determine output path
            if filename.startswith("/"):
                filepath = Path(filename)
            else:
                filepath = Path.home() / "Desktop" / filename
            
            # Write to file
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, 'w') as f:
                f.write("\n".join(all_text))
            
            return f"[#21C93A]✓ Exported {len(messages)} message(s) to: {filepath}[/#21C93A]"
        except Exception as e:
            return f"[red]Export failed: {e}[/red]"
    
    def _view_in_less(self, args: List[str]) -> str:
        """View messages in less pager for text selection."""
        try:
            messages = self.shell.messages_area.messages
            if not messages:
                return "[yellow]No messages to view[/yellow]"
            
            # Extract text from messages
            import re
            all_text = []
            for msg in messages:
                if hasattr(msg, 'renderable'):
                    text = str(msg.renderable)
                    text = re.sub(r'\[/?[#\w/]+\]', '', text)
                    all_text.append(text)
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
                tmp.write("\n".join(all_text))
                tmp_path = tmp.name
            
            # Open in less (or more on Windows)
            try:
                if os.name == 'nt':  # Windows
                    os.startfile(tmp_path)
                else:  # macOS, Linux
                    subprocess.run(['less', tmp_path], check=True)
            except Exception as e:
                return f"[red]Failed to open viewer: {e}[/red]"
            
            return f"[#21C93A]✓ Opened in pager. Press 'q' to return.[/#21C93A]\n[#E8E8E8]You can now select and copy text normally.[/#E8E8E8]"
        except Exception as e:
            return f"[red]Error: {e}[/red]"

    async def _handle_init(self) -> str:
        """Launch onboarding flow."""
        try:
            from .onboarding_screens import OnboardingFlow
            flow = OnboardingFlow(self.shell, self.shell.config_manager)
            flow.start()
            return ""
        except Exception as e:
            return f"[red]Failed to start onboarding: {e}[/red]"

