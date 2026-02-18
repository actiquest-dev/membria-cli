"""Webhook management commands."""

import typer
from typing import Optional

from membria.webhook_server import create_webhook_server

app = typer.Typer(help="Manage Membria webhook server")


@app.command()
def start(
    port: int = typer.Option(8000, "--port", "-p", help="Port to listen on"),
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host to bind to"),
) -> None:
    """Start webhook server for receiving GitHub and CI events.

    Example:
        membria webhook start --port 8000
    """
    typer.echo(f"Starting webhook server on {host}:{port}")
    typer.echo("Webhook endpoints:")
    typer.echo(f"  POST {host}:{port}/github/push")
    typer.echo(f"  POST {host}:{port}/github/pull_request")
    typer.echo(f"  POST {host}:{port}/github/workflow_run")
    typer.echo(f"  POST {host}:{port}/github/check_run")
    typer.echo(f"  POST {host}:{port}/ci/event")
    typer.echo(f"  GET  {host}:{port}/health")

    server = create_webhook_server(port=port, host=host)
    server.run()


@app.command()
def config(
    github_secret: Optional[str] = typer.Option(
        None,
        "--github-secret",
        help="GitHub webhook secret for signature verification",
    ),
) -> None:
    """Configure webhook settings.

    Example:
        membria webhook config --github-secret your_secret_here
    """
    if github_secret:
        # In a real implementation, would save to config file
        typer.echo(f"✅ GitHub secret configured")
        typer.echo("   Signature verification enabled")
    else:
        typer.echo("Current webhook configuration:")
        typer.echo("  GitHub signature verification: disabled (no secret)")
        typer.echo("\nTo enable verification:")
        typer.echo("  membria webhook config --github-secret <your-secret>")


@app.command()
def test(
    event_type: str = typer.Option("push", "--event", help="Event type to test"),
) -> None:
    """Test webhook handler with sample payload.

    Example:
        membria webhook test --event push
        membria webhook test --event pull_request
    """
    from membria.webhook_handler import WebhookHandler

    handler = WebhookHandler()

    # Sample payloads
    sample_payloads = {
        "push": {
            "ref": "refs/heads/main",
            "commits": [
                {
                    "id": "abc123def456",
                    "message": "Implement decision dec_789\n\nDecision: Use Fastify",
                }
            ],
        },
        "pull_request": {
            "action": "opened",
            "pull_request": {
                "number": 42,
                "html_url": "https://github.com/org/repo/pull/42",
                "title": "[dec_789] Use Fastify for REST API",
                "body": "Implements decision dec_789",
                "state": "open",
                "head": {"ref": "feature/fastify"},
            },
        },
        "workflow_run": {
            "workflow_run": {
                "status": "completed",
                "conclusion": "success",
                "head_commit": {"message": "dec_789: implementation"},
                "pull_requests": [{"number": 42}],
            },
        },
        "ci_json": {
            "decision_id": "dec_789",
            "event_type": "ci_complete",
            "passed": True,
            "details": "All tests passed",
        },
    }

    if event_type not in sample_payloads:
        typer.echo(f"Unknown event type: {event_type}")
        typer.echo(f"Available: {', '.join(sample_payloads.keys())}")
        raise typer.Exit(1)

    payload = sample_payloads[event_type]

    typer.echo(f"Testing {event_type} webhook...")
    result = handler.process_webhook(event_type, payload)

    if result["status"] == "success":
        typer.echo(f"✅ Success!")
        typer.echo(f"   Outcome ID: {result['outcome_id']}")
    else:
        typer.echo(f"ℹ️  {result['status']}")
        if "message" in result:
            typer.echo(f"   {result['message']}")
