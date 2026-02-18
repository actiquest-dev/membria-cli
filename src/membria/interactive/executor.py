import asyncio
import time
import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, AsyncIterator
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from .models import AgentConfig, TeamConfig, OrchestrationConfig
from .providers import ProviderFactory, Message, BaseProvider, CompletionResponse

console = Console()

from membria.graph import GraphClient

class AgentExecutor:
    """
    Orchestrates agent execution, handles providers, and implements DeepMind-inspired monitoring.
    """
    
    def __init__(self, config_manager, graph_client=None):
        self.config_manager = config_manager
        self.graph_client = graph_client or GraphClient()
        try:
            self.graph_client.connect()
        except:
            pass # Handle offline mode if needed
            
        self.session_messages: List[Message] = []
        self.total_cost: float = 0.0
        self.agent_providers: Dict[str, BaseProvider] = {}
        
        # State tracking for UI (Claude-style)
        self.active_tasks: List[Dict[str, str]] = []
        self.file_stats = {"changed": 0, "added": 0, "removed": 0}
        self.context_count = 0

        # Early return if no config (for testing/fallback)
        if not config_manager:
            return

        from .expert_registry import ExpertRegistry
        all_roles = ExpertRegistry.list_roles()
        
        team_data = self.config_manager.config.team.get("agents", {})
        provider_data = self.config_manager.config.providers
        default_p_name = self.config_manager.config.default_provider
        
        for role in all_roles:
            agent_dict = team_data.get(role, {})
            p_name = agent_dict.get("provider", default_p_name)
            p_config = provider_data.get(p_name, {})
            
            # Get API key from env or config
            api_key = p_config.get("api_key") or os.environ.get(p_config.get("api_key_env", ""), "")
            endpoint = p_config.get("endpoint")
            
            if not api_key and p_name == "anthropic":
                api_key = os.environ.get("ANTHROPIC_API_KEY", "")
            if not api_key and p_name == "openai":
                api_key = os.environ.get("OPENAI_API_KEY", "")

            try:
                auth_token = p_config.get("auth_token")
                auth_method = p_config.get("auth_method")
                provider = ProviderFactory.get_provider(p_name, api_key, endpoint, auth_token, auth_method)
                self.agent_providers[role] = provider
            except Exception as e:
                if role in team_data: # Only warn if user explicitly tried to config it
                    console.print(f"[red]Failed to init provider {p_name} for {role}: {e}[/red]")

    def set_ui(self, ui):
        """Link the executor to the UI component."""
        self.ui = ui

    async def run_task(self, prompt: str, role: str = "implementer") -> Optional[str]:
        """
        Execute a task using a specific agent role.
        """
        task_name = f"Processing: {prompt[:30]}..."
        if hasattr(self, "ui") and self.ui:
            self.ui.add_task(task_name, status="in_progress")
            
        from .expert_registry import ExpertRegistry
        expert = ExpertRegistry.get_expert(role)
        
        config = self.config_manager.config
        agent_dict = config.team.get("agents", {}).get(role, {})
        provider = self.agent_providers.get(role)

        if not provider:
            # Last ditch attempt: use default provider
            p_name = config.default_provider
            provider = self.agent_providers.get("implementer") # Assuming implementer at least exists
            if not provider:
                console.print(f"[red]No provider available for {role}.[/red]")
                return None

        # DeepMind: Liability Firebreaks
        firebreak_actions = config.orchestration.get("firebreak_actions", [])
        triggered_firebreaks = [action for action in firebreak_actions if action.lower() in prompt.lower()] # Fixed firebreak logic
        
        if triggered_firebreaks:
            from rich.prompt import Confirm
            console.print(f"[bold red]⚠️  LIABILITY FIREBREAK TRIGGERED[/bold red]: [yellow]{', '.join(triggered_firebreaks)}[/yellow]")
            console.print(f"[dim]The task contains potentially irreversible actions.[/dim]")
            if not Confirm.ask("[bold red]Do you want to proceed?[/bold red]"):
                self._log_event("L0", f"Task aborted by human principal (Firebreak: {', '.join(triggered_firebreaks)})")
                if hasattr(self, "ui") and self.ui:
                    self.ui.set_task_status(task_name, "cancelled")
                return None

        # Build message history with Graph Context (role-aware)
        context = await self._get_context(prompt, role)
        system_content = expert["prompt"]
        role_prompt = self._load_role_prompt(role)
        if role_prompt:
            system_content += f"\n\nROLE INSTRUCTIONS:\n{role_prompt}"
        if context:
            system_content += f"\n\nCONTEXT FROM GRAPH:\n{context}"
            
        messages = [
            Message(role="system", content=system_content),
            Message(role="user", content=prompt)
        ]
        
        # DeepMind Monitoring: L2 (High-level plan - hidden by default for clean UI)
        label = agent_dict.get("label", expert["name"])
        model = agent_dict.get("model", config.default_model)
        self._log_event("L2", f"Delegating task to [bold cyan]{label}[/bold cyan] ({model})")
        
        start_time = time.time()
        try:
            result = await provider.complete(model, messages)
            if result:
                if hasattr(self, "ui") and self.ui:
                    self.ui.set_task_status(task_name, "done")
                duration = time.time() - start_time
                self._log_event("L2", f"Response received from {label} in {duration:.2f}s")
                self._update_agent_stats(role, result, duration)
                return result.content
            return None
            
        except Exception as e:
            self._log_event("L0", f"CRITICAL: Agent {role} failed: {e}")
            return None

    def _log_event(self, level: str, message: str, data: Any = None):
        """
        DeepMind Monitoring Levels (L0-L3):
        L0: Heartbeat / Connectivity / Critical failures
        L1: High-level planning / Task delegation
        L2: Reasoning trace / Detailed logs
        L3: Full state / Raw artifacts
        """
        config_level = self.config_manager.config.orchestration.get("monitor_level", "L1")
        
        # Simple numeric comparison L0 < L1 < L2 < L3
        levels = {"L0": 0, "L1": 1, "L2": 2, "L3": 3}
        if levels.get(level, 0) <= levels.get(config_level, 1):
            # Clean, premium icons without technical prefixes
            icon = {"L0": "🚨", "L1": "  ›", "L2": "  ·", "L3": "  ·"}.get(level, "•")
            
            # Special formatting for delegation to make it look like a system transition
            if "Delegating task to" in message:
                msg_parts = message.replace("Delegating task to ", "").split("(")
                agent_name = msg_parts[0].strip()
                model_name = msg_parts[1].replace(")", "").strip() if len(msg_parts) > 1 else ""
                
                # Claude-style "Thought" or "Action" indicator
                console.print(f"[dim]  › Sending to {agent_name}...[/dim]")
            else:
                # Standard clean log
                console.print(f"[dim]{icon} {message}[/dim]")

    def _update_agent_stats(self, role: str, response: CompletionResponse, duration: float):
        """Updates reputation ledger and tracks token usage (DeepMind)."""
        agents_config = self.config_manager.config.team.get("agents", {})
        if role not in agents_config:
            agents_config[role] = {}
        agent_dict = agents_config[role]
        
        # 1. Track Tokens
        usage = response.usage
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        total_tokens_request = input_tokens + output_tokens
        
        if not hasattr(self, "total_tokens"):
            self.total_tokens = 0
            
        self.total_tokens += total_tokens_request
        
        # Update UI with new token count
        if hasattr(self, "ui") and self.ui:
            self.ui.update_stats(tokens=self.total_tokens)
        
        # 2. Update in-memory config for immediate feedback
        agent_dict["tasks_completed"] = agent_dict.get("tasks_completed", 0) + 1
        agent_dict["tasks_succeeded"] = agent_dict.get("tasks_succeeded", 0) + 1
        
        # 3. Persist to FalkorDB
        if self.graph_client and self.graph_client.connected:
            label = agent_dict.get("label", role)
            model = agent_dict.get("model", "unknown")
            
            query = """
            MERGE (a:Agent {role: $role, model: $model})
            ON CREATE SET a.label = $label, a.tasks_completed = 1, a.tasks_succeeded = 1, a.avg_duration = $duration, a.total_tokens = $tokens
            ON MATCH SET a.tasks_completed = a.tasks_completed + 1, 
                         a.tasks_succeeded = a.tasks_succeeded + 1,
                         a.avg_duration = (a.avg_duration * (a.tasks_completed - 1) + $duration) / a.tasks_completed,
                         a.total_tokens = a.total_tokens + $tokens
            """
            try:
                self.graph_client.query(query, {
                    "role": role, 
                    "model": model, 
                    "label": label, 
                    "duration": duration,
                    "tokens": total_tokens_request
                })
            except Exception as e:
                self._log_event("L0", f"Failed to persist stats to FalkorDB: {e}")

    async def _get_context(self, prompt: str, role: str) -> str:
        """Retrieves relevant engrams/decisions from FalkorDB context."""
        if not self.graph_client or not self.graph_client.connected:
            return ""

        self._log_event("L2", f"Fetching role-aware context for: [dim]{prompt[:50]}...[/dim]")
        try:
            from membria.context_manager import ContextManager
            from membria.calibration_updater import CalibrationUpdater

            role_cfg = self.graph_client.get_role(role) or {}
            module = "general"
            max_tokens = 1200
            include_chains = True

            links = self.graph_client.get_role_links(role)
            docshots = links.get("docshots") or []
            role_skills = links.get("skills") or []
            role_nk = links.get("negative_knowledge") or []

            doc_shot = None
            if docshots:
                ds = docshots[0]
                doc_shot = {"doc_shot_id": ds.get("id"), "count": ds.get("doc_count", 0)}

            ctx_mgr = ContextManager(self.graph_client, CalibrationUpdater())
            ctx = ctx_mgr.build_decision_context(
                statement=prompt,
                module=module,
                confidence=0.5,
                max_tokens=max_tokens,
                include_chains=include_chains,
                doc_shot=doc_shot,
                session_context=None,
                role_skills=role_skills,
                role_negative_knowledge=role_nk,
            )
            return ctx.get("compact_context") or ""
        except Exception as e:
            self._log_event("L0", f"Context retrieval failed: {e}")
            return ""

    def _load_role_prompt(self, role: str) -> str:
        """Load role-specific prompt from graph (if configured)."""
        try:
            role_cfg = self.graph_client.get_role(role) or {}
            prompt_path = role_cfg.get("prompt_path") or ""
            if not prompt_path:
                return ""
            path = Path(prompt_path).expanduser()
            if not path.exists():
                return ""
            return path.read_text(encoding="utf-8", errors="ignore").strip()
        except Exception:
            return ""

    def _select_specialist(self, domain: str) -> str:
        """Selects the best agent role for a given domain/category."""
        agents = self.config_manager.config.team.get("agents", {})
        best_role = "implementer" # Default
        best_score = -1.0
        
        for role, agent in agents.items():
            scores = agent.get("domain_scores", {})
            score = scores.get(domain, 0.0)
            if score > best_score:
                best_score = score
                best_role = role
                
        if best_score > 0:
            self._log_event("L1", f"Selected specialist [bold green]{best_role}[/bold green] for domain [cyan]{domain}[/cyan] (Score: {best_score})")
            
        return best_role

    async def _get_red_team_context(self, task: str) -> str:
        """Fetch known antipatterns and past failures for Red Team targeting."""
        if not self.graph_client or not self.graph_client.connected:
            return ""
            
        self._log_event("L2", "Red Team: Identifying historical vulnerabilities in graph...")
        try:
            # Query for failed decisions or explicitly tagged antipatterns
            query = """
            MATCH (d:Decision)-[:RESULTED_IN]->(o:Outcome {status: 'failure'})
            WHERE d.topic CONTAINS $domain OR d.tags CONTAINS 'security'
            RETURN d.topic, d.reasoning, o.reason_of_failure
            LIMIT 5
            """
            domain = task.split(":")[0] if ":" in task else ""
            results = self.graph_client.query(query, {"domain": domain})
            
            if results:
                context = "\nCRITICAL VULNERABILITIES FROM PAST FAILURES:\n"
                for row in results:
                    context += f"- TOPIC: {row[0]}\n  PREVIOUS REASONING: {row[1]}\n  WHY IT FAILED: {row[2]}\n"
                return context
        except Exception as e:
            self._log_event("L0", f"Red Team context retrieval failed: {e}")
        return ""

    async def run_orchestration(self, task: str, mode: str = "pipeline", red_team: bool = False) -> str:
        """
        Coordinates multiple agents to complete a complex task (TeamLead logic).
        """
        self._log_event("L1", f"Starting orchestration: [cyan]{mode}[/cyan] mode")
        
        if mode == "diamond":
            from .workflow_engine import DoubleDiamondEngine
            engine = DoubleDiamondEngine(self)
            return await engine.run(task)

        if mode == "auto":
            # DeepMind: Adaptive Coordination
            self._log_event("L1", "Auto-routing: Classifying task for optimal flow...")
            classifier_prompt = f"""Classify this task into one of these types:
            - SINGLE: Simple query or command.
            - PIPELINE: Complex implementation requiring planning and review.
            - CONSENSUS: Design decision requiring multiple viewpoints.
            
            Task: {task}
            
            Return ONLY the type name in uppercase."""
            
            classification = await self.run_task(classifier_prompt, role="architect")
            classification = classification.strip().upper() if classification else "SINGLE"
            
            self._log_event("L1", f"Classification: [bold yellow]{classification}[/bold yellow]")
            
            if "PIPELINE" in classification:
                return await self.run_orchestration(task, mode="pipeline")
            elif "CONSENSUS" in classification:
                return await self.run_orchestration(task, mode="consensus")
            else:
                role = "implementer"
                # Check for domain-specific specialist
                if ":" in task: # Example "python: fix bug"
                    domain = task.split(":")[0].strip()
                    role = self._select_specialist(domain)
                return await self.run_task(task, role=role)

        if mode == "pipeline":
            # 1. Architect plans
            self._log_event("L1", "Phase 1: Planning (Architect)")
            arch_prompt = f"Decompose this task into a technical plan with 2-3 steps: {task}"
            plan = await self.run_task(arch_prompt, role="architect")
            if not plan: return "Failed to generate plan."
            
            # 2. Implementer executes
            self._log_event("L1", "Phase 2: Execution (Implementer)")
            impl_prompt = f"Follow this plan to implement the solution:\nPLAN:\n{plan}\n\nORIGINAL TASK: {task}"
            code = await self.run_task(impl_prompt, role="implementer")
            if not code: return "Failed to execute plan."
            
            # 3. Reviewer validates
            self._log_event("L1", "Phase 3: Review (Reviewer)")
            rev_prompt = f"Review the implementation against the plan and task requirements:\nPLAN: {plan}\nCODE: {code}"
            review = await self.run_task(rev_prompt, role="reviewer")
            
            return f"### PROPOSED SOLUTION\n{code}\n\n---\n### ARCHITECT PLAN\n{plan}\n\n---\n### REVIEW\n{review}"

        if mode == "debate":
            # DeepMind/Council: Multi-objective Optimization via Debate
            self._log_event("L1", f"AI Council: Initiating multi-agent confrontation... {'(Red Team Active)' if red_team else ''}")
            
            # Roles for debate (can be dynamic)
            participants = [
                {"role": "architect", "prompt": f"Proposed architectural solution for: {task}. Focus on scalability."},
                {"role": "implementer", "prompt": f"Proposed implementation for: {task}. Focus on speed and simplicity."}
            ]
            
            if red_team:
                red_context = await self._get_red_team_context(task)
                participants.append({
                    "role": "security_auditor", 
                    "prompt": f"Act as an ADVERSARY. Find flaws and vulnerabilities in the proposed paths for: {task}\n{red_context}"
                })
            
            self._log_event("L1", f"Phase 1: Concurrent Proposals ({len(participants)} agents)")
            results = await self.run_parallel(participants)
            
            self._log_event("L1", "Phase 2: Adversarial Review & Synthesis")
            
            synth_prompt = f"""You are the Moderator. Analyze the following debate and synthesize the final decision:
            
            ARCHITECT VIEW: {results[0]}
            
            IMPLEMENTER VIEW: {results[1]}
            """
            
            if red_team:
                synth_prompt += f"\nSECURITY ATTACKER VIEW: {results[2]}"
                
            synth_prompt += f"\n\nORIGINAL TASK: {task}\n\nIdentify conflicts, address security flaws (if any), and output the ultimate optimized path."
            
            final_solution = await self.run_task(synth_prompt, role="reviewer")
            view_summary = f"- **Architect**: {results[0][:200]}...\n- **Implementer**: {results[1][:200]}..."
            if red_team:
                view_summary += f"\n- **Security Auditor**: {results[2][:200]}..."
                
            return f"### 🎭 DEBATE RESULTS\n{final_solution}\n\n---\n### 🔍 RAW PERSPECTIVES\n{view_summary}"

        if mode == "consensus":
            # DeepMind: Multi-objective Optimization / Comparison
            self._log_event("L1", "Consensus Flow: Generating multiple viewpoints...")
            
            task_list = [
                {"role": "architect", "prompt": f"Proposed architectural approach for: {task}"},
                {"role": "implementer", "prompt": f"Proposed implementation for: {task}"}
            ]
            results = await self.run_parallel(task_list)
            
            self._log_event("L1", "Phase 2: Review & Synthesis (Reviewer)")
            synth_prompt = f"""Compare these two approaches and synthesize the best final solution:
            APPROACH 1 (Architect): {results[0]}
            APPROACH 2 (Implementer): {results[1]}
            
            ORIGINAL TASK: {task}"""
            
            final_solution = await self.run_task(synth_prompt, role="reviewer")
            return f"### CONSENSUS SOLUTION\n{final_solution}\n\n---\n### RAW INPUTS\n- Architect: {results[0][:200]}...\n- Implementer: {results[1][:200]}..."
            
        return f"Orchestration mode '{mode}' not fully implemented."

    async def run_parallel(self, task_list: List[Dict[str, str]]) -> List[Optional[str]]:
        """
        Runs multiple agent tasks in parallel (Fan-out).
        task_list: [{'role': 'architect', 'prompt': '...'}, ...]
        """
        self._log_event("L1", f"Parallel Fan-out: Executing {len(task_list)} tasks...")
        
        tasks = []
        for item in task_list:
            tasks.append(self.run_task(item['prompt'], role=item['role']))
            
        results = await asyncio.gather(*tasks)
        self._log_event("L1", "Parallel tasks completed.")
        return results

    def save_session(self):
        """Persist session state to FalkorDB/Disk (Stub for Phase 1)."""
        self._log_event("L2", "Session state preserved.")

import os # Needed for _init_providers
