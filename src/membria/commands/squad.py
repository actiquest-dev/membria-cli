"""Squad orchestration commands."""

import json
import uuid
import asyncio
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table

from membria.config import ConfigManager
from membria.graph import GraphClient

console = Console()
app = typer.Typer(help="Squad orchestration (roles + profiles per task)")


def _load_presets() -> dict:
    presets_path = Path(__file__).resolve().parent.parent / "presets" / "squads.json"
    if not presets_path.exists():
        return {"presets": []}
    with open(presets_path, "r") as f:
        return json.load(f)


def _default_profile_path() -> str:
    cfg = ConfigManager()
    return str(cfg.config_file)


@app.command("preset-list")
def preset_list() -> None:
    """List built-in squad presets."""
    data = _load_presets()
    table = Table(title="Squad Presets")
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("Strategy")
    table.add_column("Roles")
    for p in data.get("presets", []):
        table.add_row(
            p.get("id", ""),
            p.get("name", ""),
            p.get("strategy", ""),
            ", ".join(p.get("roles") or []),
        )
    console.print(table)


@app.command("create")
def create_squad(
    name: str = typer.Option(..., "--name", help="Squad name"),
    project_id: str = typer.Option(..., "--project-id", help="Project id"),
    strategy: str = typer.Option(..., "--strategy", help="lead_review|parallel_arbiter|red_team"),
    roles: List[str] = typer.Option(..., "--role", help="Role names (repeatable)"),
    profiles: List[str] = typer.Option(..., "--profile", help="Profile names (repeatable)"),
    profile_paths: Optional[List[str]] = typer.Option(None, "--profile-path", help="Profile config path (repeatable)"),
    project_name: Optional[str] = typer.Option(None, "--project-name", help="Project display name"),
    workspace_id: Optional[str] = typer.Option(None, "--workspace-id", help="Workspace id"),
    workspace_name: Optional[str] = typer.Option(None, "--workspace-name", help="Workspace name"),
):
    """Create a squad from explicit roles/profiles."""
    if len(roles) != len(profiles):
        console.print("[red]Roles and profiles must have the same length.[/red]")
        raise typer.Exit(1)

    if profile_paths and len(profile_paths) not in (1, len(profiles)):
        console.print("[red]profile-path must be single or match profiles length.[/red]")
        raise typer.Exit(1)

    graph = GraphClient()
    if not graph.connect():
        console.print("[red]Failed to connect to FalkorDB.[/red]")
        raise typer.Exit(1)

    if workspace_id:
        graph.upsert_workspace(workspace_id, workspace_name or workspace_id)
    graph.upsert_project(project_id, project_name or project_id, workspace_id=workspace_id)

    squad_id = f"sqd_{uuid.uuid4().hex[:10]}"
    ok = graph.create_squad(squad_id, name=name, strategy=strategy, project_id=project_id)
    if not ok:
        console.print("[red]Failed to create squad.[/red]")
        raise typer.Exit(1)

    default_path = _default_profile_path()
    for idx, (role, profile) in enumerate(zip(roles, profiles), start=1):
        role_id = f"role_{role}"
        profile_id = f"profile_{profile}"
        path = default_path
        if profile_paths:
            path = profile_paths[0] if len(profile_paths) == 1 else profile_paths[idx - 1]
        graph.upsert_role(role_id, role)
        graph.upsert_profile(profile_id, profile, config_path=path)
        assignment_id = f"asn_{uuid.uuid4().hex[:10]}"
        graph.add_assignment(
            assignment_id=assignment_id,
            squad_id=squad_id,
            role_id=role_id,
            profile_id=profile_id,
            order=idx,
        )

    console.print(f"[green]✓ Squad created: {squad_id}[/green]")


@app.command("create-from-preset")
def create_from_preset(
    preset_id: str = typer.Argument(..., help="Preset id"),
    name: Optional[str] = typer.Option(None, "--name", help="Squad name override"),
    project_id: str = typer.Option(..., "--project-id", help="Project id"),
    profile_path: Optional[str] = typer.Option(None, "--profile-path", help="Default profile config path"),
    project_name: Optional[str] = typer.Option(None, "--project-name", help="Project display name"),
    workspace_id: Optional[str] = typer.Option(None, "--workspace-id", help="Workspace id"),
    workspace_name: Optional[str] = typer.Option(None, "--workspace-name", help="Workspace name"),
):
    """Create a squad from a preset."""
    data = _load_presets()
    preset = next((p for p in data.get("presets", []) if p.get("id") == preset_id), None)
    if not preset:
        console.print(f"[red]Preset not found: {preset_id}[/red]")
        raise typer.Exit(1)

    roles = preset.get("roles") or []
    profiles = preset.get("profiles") or []
    if len(roles) != len(profiles):
        console.print("[red]Preset roles/profiles length mismatch.[/red]")
        raise typer.Exit(1)

    graph = GraphClient()
    if not graph.connect():
        console.print("[red]Failed to connect to FalkorDB.[/red]")
        raise typer.Exit(1)

    if workspace_id:
        graph.upsert_workspace(workspace_id, workspace_name or workspace_id)
    graph.upsert_project(project_id, project_name or project_id, workspace_id=workspace_id)

    squad_name = name or preset.get("name") or preset_id
    squad_id = f"sqd_{uuid.uuid4().hex[:10]}"
    ok = graph.create_squad(squad_id, name=squad_name, strategy=preset.get("strategy"), project_id=project_id)
    if not ok:
        console.print("[red]Failed to create squad.[/red]")
        raise typer.Exit(1)

    default_path = profile_path or _default_profile_path()
    for idx, (role, profile) in enumerate(zip(roles, profiles), start=1):
        role_id = f"role_{role}"
        profile_id = f"profile_{profile}"
        graph.upsert_role(role_id, role)
        graph.upsert_profile(profile_id, profile, config_path=default_path)
        assignment_id = f"asn_{uuid.uuid4().hex[:10]}"
        graph.add_assignment(
            assignment_id=assignment_id,
            squad_id=squad_id,
            role_id=role_id,
            profile_id=profile_id,
            order=idx,
        )

    console.print(f"[green]✓ Squad created from preset: {squad_id}[/green]")


@app.command("list")
def list_squads(project_id: Optional[str] = typer.Option(None, "--project-id")) -> None:
    """List squads."""
    graph = GraphClient()
    if not graph.connect():
        console.print("[red]Failed to connect to FalkorDB.[/red]")
        raise typer.Exit(1)

    squads = graph.list_squads(project_id=project_id, limit=50)
    table = Table(title="Squads")
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("Strategy")
    table.add_column("Project")
    for s in squads:
        table.add_row(
            s.get("id", ""),
            s.get("name", ""),
            s.get("strategy", ""),
            s.get("project_id", ""),
        )
    console.print(table)


@app.command("assignments")
def list_assignments(squad_id: str = typer.Argument(..., help="Squad id")) -> None:
    """List assignments for a squad."""
    graph = GraphClient()
    if not graph.connect():
        console.print("[red]Failed to connect to FalkorDB.[/red]")
        raise typer.Exit(1)

    assignments = graph.list_assignments(squad_id)
    table = Table(title=f"Assignments for {squad_id}")
    table.add_column("ID")
    table.add_column("Role")
    table.add_column("Profile")
    table.add_column("Order")
    for a in assignments:
        table.add_row(
            a.get("id", ""),
            a.get("role_id", ""),
            a.get("profile_id", ""),
            str(a.get("order", "")),
        )
    console.print(table)


@app.command("run")
def run_squad(
    squad_id: str = typer.Argument(..., help="Squad id"),
    task: str = typer.Option(..., "--task", help="Task description"),
    record_decisions: bool = typer.Option(False, "--record-decisions", help="Record outputs as decisions with role/assignment"),
) -> None:
    """Run a squad (lead_review / parallel_arbiter / red_team)."""
    graph = GraphClient()
    if not graph.connect():
        console.print("[red]Failed to connect to FalkorDB.[/red]")
        raise typer.Exit(1)

    squads = graph.list_squads(limit=200)
    squad = next((s for s in squads if s.get("id") == squad_id), None)
    if not squad:
        console.print(f"[red]Squad not found: {squad_id}[/red]")
        raise typer.Exit(1)

    assignments = graph.list_assignments(squad_id)
    if not assignments:
        console.print("[red]No assignments found for squad.[/red]")
        raise typer.Exit(1)

    console.print(f"[bold]Squad:[/bold] {squad.get('name')}  [dim]({squad.get('strategy')})[/dim]")
    console.print(f"[bold]Task:[/bold] {task}")

    async def _run():
        from membria.config import ConfigManager
        from membria.interactive.executor import AgentExecutor
        from membria.models import Decision
        import uuid
        from datetime import datetime
        from membria.memory_manager import MemoryManager

        executor = AgentExecutor(ConfigManager())
        memory = MemoryManager(graph)

        def role_name(role_id: str) -> str:
            return role_id.replace("role_", "", 1)

        ordered = sorted(assignments, key=lambda a: int(a.get("order") or 0))
        roles = [role_name(a.get("role_id", "")) for a in ordered]
        strategy = squad.get("strategy")

        if strategy == "lead_review" and len(roles) >= 2:
            lead = roles[0]
            reviewer = roles[1]
            lead_out = await executor.run_task(task, role=lead)
            review_prompt = f"Review the proposal and find issues/risks:\n\n{lead_out}"
            review_out = await executor.run_task(review_prompt, role=reviewer)
            if record_decisions:
                _record_decision(memory, task, lead_out, ordered[0], lead, "lead_review:lead")
                _record_decision(memory, task, review_out, ordered[1], reviewer, "lead_review:review")
            return {"lead": lead_out, "review": review_out}

        if strategy == "parallel_arbiter" and len(roles) >= 3:
            proposers = roles[:-1]
            arbiter = roles[-1]
            results = await asyncio.gather(*[executor.run_task(task, role=r) for r in proposers])
            merged = "\n\n".join([f"[{r}]\n{res}" for r, res in zip(proposers, results)])
            arbiter_prompt = f"Select best proposal, justify choice:\n\n{merged}"
            arbiter_out = await executor.run_task(arbiter_prompt, role=arbiter)
            if record_decisions:
                for idx, (r, res) in enumerate(zip(proposers, results)):
                    _record_decision(memory, task, res, ordered[idx], r, "parallel_arbiter:proposal")
                _record_decision(memory, task, arbiter_out, ordered[-1], arbiter, "parallel_arbiter:arbiter")
            return {"proposals": results, "arbiter": arbiter_out}

        if strategy == "red_team" and len(roles) >= 2:
            builder = roles[0]
            attacker = roles[1]
            proposal = await executor.run_task(task, role=builder)
            attack_prompt = f"Red-team this proposal, find risks and failures:\n\n{proposal}"
            attack = await executor.run_task(attack_prompt, role=attacker)
            if record_decisions:
                _record_decision(memory, task, proposal, ordered[0], builder, "red_team:proposal")
                _record_decision(memory, task, attack, ordered[1], attacker, "red_team:attack")
            return {"proposal": proposal, "red_team": attack}

        # Fallback: run first role only
        out = await executor.run_task(task, role=roles[0])
        if record_decisions:
            _record_decision(memory, task, out, ordered[0], roles[0], "single:result")
        return {"result": out}

    result = asyncio.run(_run())
    console.print("[green]✓ Squad run completed[/green]")
    console.print_json(data=result)


def _record_decision(memory: "MemoryManager", task: str, output: Optional[str], assignment: dict, role: str, source: str) -> None:
    if not output:
        return
    from membria.models import Decision
    import uuid
    from datetime import datetime
    decision = Decision(
        decision_id=f"dec_{uuid.uuid4().hex[:12]}",
        statement=f"{task}\n\nOUTPUT:\n{output[:2000]}",
        alternatives=["n/a"],
        confidence=0.5,
        module="general",
        created_at=datetime.utcnow(),
        created_by="squad_run",
    )
    decision.role_id = assignment.get("role_id") or f"role_{role}"
    decision.assignment_id = assignment.get("id")
    memory.store_decision(decision, source=source)


@app.command("role-set")
def role_set(
    name: str = typer.Argument(..., help="Role name"),
    description: Optional[str] = typer.Option(None, "--description"),
    prompt_path: Optional[str] = typer.Option(None, "--prompt-path", help="Path to role prompt markdown"),
    context_policy: Optional[str] = typer.Option(None, "--context-policy", help="JSON context policy (deprecated)"),
    docshot_ids: Optional[List[str]] = typer.Option(None, "--docshot", help="DocShot IDs (repeatable)"),
    skill_ids: Optional[List[str]] = typer.Option(None, "--skill", help="Skill IDs (repeatable)"),
    nk_ids: Optional[List[str]] = typer.Option(None, "--nk", help="NegativeKnowledge IDs (repeatable)"),
) -> None:
    """Create or update a role with prompt path and context policy."""
    graph = GraphClient()
    if not graph.connect():
        console.print("[red]Failed to connect to FalkorDB.[/red]")
        raise typer.Exit(1)

    policy = None
    if context_policy:
        try:
            policy = json.loads(context_policy)
        except Exception:
            console.print("[red]Invalid JSON in --context-policy[/red]")
            raise typer.Exit(1)

    role_id = f"role_{name}"
    ok = graph.upsert_role(
        role_id=role_id,
        name=name,
        description=description,
        prompt_path=prompt_path,
        context_policy=policy,
    )
    if not ok:
        console.print("[red]Failed to upsert role.[/red]")
        raise typer.Exit(1)

    for ds in docshot_ids or []:
        graph.link_role_docshot(name, ds)
    for sk in skill_ids or []:
        graph.link_role_skill(name, sk)
    for nk in nk_ids or []:
        graph.link_role_nk(name, nk)
    console.print(f"[green]✓ Role updated: {role_id}[/green]")


@app.command("role-show")
def role_show(name: str = typer.Argument(..., help="Role name")) -> None:
    """Show role configuration and linked context."""
    graph = GraphClient()
    if not graph.connect():
        console.print("[red]Failed to connect to FalkorDB.[/red]")
        raise typer.Exit(1)

    role = graph.get_role(name)
    links = graph.get_role_links(name)
    console.print("[bold]Role[/bold]")
    console.print_json(data=role or {})
    console.print("[bold]Linked Context[/bold]")
    console.print_json(data=links or {})


@app.command("role-link")
def role_link(
    name: str = typer.Argument(..., help="Role name"),
    docshot_ids: Optional[List[str]] = typer.Option(None, "--docshot", help="DocShot IDs (repeatable)"),
    skill_ids: Optional[List[str]] = typer.Option(None, "--skill", help="Skill IDs (repeatable)"),
    nk_ids: Optional[List[str]] = typer.Option(None, "--nk", help="NegativeKnowledge IDs (repeatable)"),
) -> None:
    """Link role to DocShot/Skill/NegativeKnowledge."""
    graph = GraphClient()
    if not graph.connect():
        console.print("[red]Failed to connect to FalkorDB.[/red]")
        raise typer.Exit(1)
    for ds in docshot_ids or []:
        graph.link_role_docshot(name, ds)
    for sk in skill_ids or []:
        graph.link_role_skill(name, sk)
    for nk in nk_ids or []:
        graph.link_role_nk(name, nk)
    console.print("[green]✓ Role links updated[/green]")


@app.command("role-unlink")
def role_unlink(
    name: str = typer.Argument(..., help="Role name"),
    docshot_ids: Optional[List[str]] = typer.Option(None, "--docshot", help="DocShot IDs (repeatable)"),
    skill_ids: Optional[List[str]] = typer.Option(None, "--skill", help="Skill IDs (repeatable)"),
    nk_ids: Optional[List[str]] = typer.Option(None, "--nk", help="NegativeKnowledge IDs (repeatable)"),
) -> None:
    """Unlink role from DocShot/Skill/NegativeKnowledge."""
    graph = GraphClient()
    if not graph.connect():
        console.print("[red]Failed to connect to FalkorDB.[/red]")
        raise typer.Exit(1)
    for ds in docshot_ids or []:
        graph.unlink_role_docshot(name, ds)
    for sk in skill_ids or []:
        graph.unlink_role_skill(name, sk)
    for nk in nk_ids or []:
        graph.unlink_role_nk(name, nk)
    console.print("[green]✓ Role links removed[/green]")
