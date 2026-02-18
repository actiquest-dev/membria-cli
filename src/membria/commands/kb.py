"""KB ingestion commands."""

import os
import typer
from typing import Optional, List
from rich.console import Console

from membria.graph import GraphClient
from membria.kb_ingest import ingest_documents

console = Console()
app = typer.Typer(help="Knowledge Base ingestion")


@app.command("ingest")
def ingest(
    path: str = typer.Argument(..., help="Path to docs folder or file"),
    doc_type: str = typer.Option("kb", "--type", help="Document type tag"),
    tags: Optional[List[str]] = typer.Option(None, "--tag", help="Tags (repeatable)"),
    chunk_size: int = typer.Option(800, "--chunk", help="Chunk size (chars)"),
    overlap: int = typer.Option(100, "--overlap", help="Chunk overlap (chars)"),
    model: str = typer.Option("embed-english-light-v3.0", "--model", help="Cohere model"),
):
    """Ingest documents into the graph with embeddings."""
    api_key = os.environ.get("COHERE_API_KEY", "")
    if not api_key:
        console.print("[red]COHERE_API_KEY is required.[/red]")
        raise typer.Exit(1)

    graph_client = GraphClient()
    if not graph_client.connect():
        console.print("[red]Failed to connect to FalkorDB.[/red]")
        raise typer.Exit(1)

    result = ingest_documents(
        root=path,
        graph_client=graph_client,
        api_key=api_key,
        doc_type=doc_type,
        tags=tags or [],
        chunk_size=chunk_size,
        overlap=overlap,
        model=model,
    )
    console.print(f"[green]✓ Ingested {result['files']} files, {result['chunks']} chunks[/green]")
