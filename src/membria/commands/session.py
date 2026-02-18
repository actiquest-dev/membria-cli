"""Session persistence commands."""

import typer
from rich.console import Console
from typing import Optional

from membria.graph import GraphClient

session_app = typer.Typer(help="Session persistence (resume, checkpoint)")
console = Console()


@session_app.command("resume")
def resume(session_id: Optional[str] = typer.Argument(None)) -> None:
    """Resume the latest active session context or by session_id."""
    try:
        client = GraphClient()
        client.connect()

        sc = None
        if session_id:
            sc = client.get_session_context(session_id)
        else:
            sc = _get_latest_session_context(client)

        if not sc:
            console.print("[bold yellow]No active session context found[/bold yellow]")
            raise typer.Exit(code=1)

        console.print("[bold]Session Context[/bold]\n")
        console.print(f"Session: {sc.get('session_id')}")
        console.print(f"Task: {sc.get('task')}")
        if sc.get("focus"):
            console.print(f"Focus: {sc.get('focus')}")
        if sc.get("current_plan"):
            console.print(f"Plan: {sc.get('current_plan')}")
        if sc.get("constraints"):
            console.print("Constraints:")
            for c in sc.get("constraints"):
                console.print(f"  - {c}")
        if sc.get("doc_shot_id"):
            console.print(f"DocShot: {sc.get('doc_shot_id')}")

    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Error: {e}")
        raise typer.Exit(code=1)


@session_app.command("checkpoint")
def checkpoint(
    session_id: str = typer.Argument(...),
    task: str = typer.Option(..., "--task"),
    focus: Optional[str] = typer.Option(None, "--focus"),
    plan: Optional[str] = typer.Option(None, "--plan"),
    ttl_days: int = typer.Option(3, "--ttl-days"),
) -> None:
    """Save/refresh a session context snapshot."""
    try:
        client = GraphClient()
        client.connect()

        ok = client.upsert_session_context(
            session_id=session_id,
            task=task,
            focus=focus,
            current_plan=plan,
            constraints=[],
            doc_shot_id=None,
            ttl_days=ttl_days,
        )

        if ok:
            console.print("[bold green]✓[/bold green] Session checkpoint saved")
        else:
            console.print("[bold red]✗[/bold red] Failed to save checkpoint")
            raise typer.Exit(code=1)

    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Error: {e}")
        raise typer.Exit(code=1)


def _get_latest_session_context(client: GraphClient):
    if not client.connected:
        return None
    try:
        query = """
        MATCH (sc:SessionContext)
        WHERE (sc.is_active IS NULL OR sc.is_active = true)
        RETURN sc.session_id as session_id,
               sc.task as task,
               sc.focus as focus,
               sc.current_plan as current_plan,
               sc.constraints as constraints,
               sc.doc_shot_id as doc_shot_id,
               sc.created_at as created_at
        ORDER BY sc.created_at DESC
        LIMIT 1
        """
        result = client.graph.query(query)
        if result and len(result) > 0:
            row = result[0]
            return {
                "session_id": row[0],
                "task": row[1],
                "focus": row[2],
                "current_plan": row[3],
                "constraints": row[4],
                "doc_shot_id": row[5],
                "created_at": row[6],
            }
    except Exception:
        return None
    return None
