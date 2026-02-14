"""
Command-line interface for RAG Debugger.

Provides commands for:
- Initializing the debugger
- Starting the API server
- Viewing traces
- Managing snapshots
"""

import click
import sys
import json
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich import box
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core import get_db, close_db, format_cost
from core.models import SessionDetail

console = Console()
logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """
    RAG Debugger - DevTools for Retrieval-Augmented Generation
    
    Debug your RAG pipelines with ease.
    """
    pass


@cli.command()
def init():
    """
    Initialize RAG Debugger.
    
    Creates configuration directory and database.
    """
    try:
        console.print("\n[bold blue]🚀 Initializing RAG Debugger...[/bold blue]")
        
        # Get database (this creates it if it doesn't exist)
        db = get_db()
        
        console.print(f"\n✅ Database initialized at: [cyan]{db.db_path}[/cyan]")
        console.print(f"✅ Config directory: [cyan]{db.db_path.parent}[/cyan]")
        
        console.print("\n[bold green]✨ RAG Debugger initialized successfully![/bold green]")
        console.print("\nNext steps:")
        console.print("  1. Start the server: [yellow]ragdebug run[/yellow]")
        console.print("  2. Integrate with your RAG app")
        console.print("  3. View traces: [yellow]ragdebug trace last[/yellow]")
        
    except Exception as e:
        console.print(f"\n[bold red]❌ Error:[/bold red] {e}")
        sys.exit(1)


@cli.command()
@click.option('--host', default='0.0.0.0', help='Host to bind to')
@click.option('--port', default=8765, help='Port to bind to')
@click.option('--reload', is_flag=True, help='Enable auto-reload')
def run(host: str, port: int, reload: bool):
    """
    Start the RAG Debugger API server.
    
    The server provides REST API for logging events and web UI for visualization.
    """
    try:
        console.print("\n[bold blue]🚀 Starting RAG Debugger API Server...[/bold blue]")
        console.print(f"\n   Host: [cyan]{host}[/cyan]")
        console.print(f"   Port: [cyan]{port}[/cyan]")
        console.print(f"   Reload: [cyan]{reload}[/cyan]")
        
        console.print(f"\n   API Docs: [cyan]http://localhost:{port}/docs[/cyan]")
        console.print(f"   Web UI: [cyan]http://localhost:{port}/[/cyan]")
        
        console.print("\n[dim]Press Ctrl+C to stop[/dim]\n")
        
        # Import and run uvicorn
        import uvicorn
        uvicorn.run(
            "api.main:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info"
        )
        
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Server stopped[/yellow]")
    except Exception as e:
        console.print(f"\n[bold red]❌ Error:[/bold red] {e}")
        sys.exit(1)


@cli.command()
@click.argument('session_id', required=False)
@click.option('--json', 'json_output', is_flag=True, help='Output as JSON')
def trace(session_id: Optional[str], json_output: bool):
    """
    View a session trace.
    
    If no session_id is provided, shows the most recent session.
    Use 'last' as session_id to explicitly get the latest session.
    """
    try:
        db = get_db()
        
        # Get session
        if not session_id or session_id == 'last':
            session = db.get_latest_session()
            if not session:
                console.print("[yellow]No sessions found.[/yellow]")
                return
            session_id = session.id
        
        # Get full session detail
        detail = db.get_session_detail(session_id)
        if not detail:
            console.print(f"[red]Session {session_id} not found.[/red]")
            return
        
        # JSON output
        if json_output:
            print(json.dumps(detail.model_dump(), indent=2, default=str))
            return
        
        # Pretty output
        _display_session_detail(detail)
        
    except Exception as e:
        console.print(f"[bold red]❌ Error:[/bold red] {e}")
        sys.exit(1)
    finally:
        close_db()


@cli.command()
@click.option('--limit', default=10, help='Number of sessions to show')
def list(limit: int):
    """
    List recent sessions.
    """
    try:
        db = get_db()
        sessions = db.list_sessions(limit=limit)
        
        if not sessions:
            console.print("[yellow]No sessions found.[/yellow]")
            return
        
        # Create table
        table = Table(title=f"Recent Sessions (last {len(sessions)})", box=box.ROUNDED)
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Query", style="white")
        table.add_column("Model", style="magenta")
        table.add_column("Cost", style="green", justify="right")
        table.add_column("Duration", style="blue", justify="right")
        table.add_column("Created", style="dim")
        
        for session in sessions:
            cost_str = format_cost(session.total_cost) if session.total_cost else "-"
            duration_str = f"{session.total_duration_ms}ms" if session.total_duration_ms else "-"
            query_preview = session.query[:50] + "..." if len(session.query) > 50 else session.query
            created_str = session.created_at.strftime("%Y-%m-%d %H:%M:%S")
            
            table.add_row(
                session.id[:8] + "...",
                query_preview,
                session.model or "-",
                cost_str,
                duration_str,
                created_str
            )
        
        console.print("\n")
        console.print(table)
        console.print(f"\n[dim]Use 'ragdebug trace <session_id>' to view details[/dim]")
        
    except Exception as e:
        console.print(f"[bold red]❌ Error:[/bold red] {e}")
        sys.exit(1)
    finally:
        close_db()


@cli.command()
@click.argument('session_id')
@click.option('--output', '-o', help='Output file path')
def export(session_id: str, output: Optional[str]):
    """
    Export a session to JSON file.
    """
    try:
        db = get_db()
        
        # Handle 'last'
        if session_id == 'last':
            session = db.get_latest_session()
            if not session:
                console.print("[yellow]No sessions found.[/yellow]")
                return
            session_id = session.id
        
        detail = db.get_session_detail(session_id)
        if not detail:
            console.print(f"[red]Session {session_id} not found.[/red]")
            return
        
        # Determine output path
        if not output:
            output = f"session_{session_id[:8]}.json"
        
        # Export
        with open(output, 'w') as f:
            json.dump(detail.model_dump(), f, indent=2, default=str)
        
        console.print(f"\n[green]✓[/green] Exported to: [cyan]{output}[/cyan]")
        
    except Exception as e:
        console.print(f"[bold red]❌ Error:[/bold red] {e}")
        sys.exit(1)
    finally:
        close_db()


@cli.command()
def clear():
    """
    Clear all sessions and snapshots from the database.
    
    This is destructive and cannot be undone!
    """
    if not click.confirm("⚠️  This will delete ALL sessions and snapshots. Continue?"):
        console.print("[yellow]Cancelled.[/yellow]")
        return
    
    try:
        db = get_db()
        
        # Delete all sessions (cascades to events)
        cursor = db.conn.cursor()
        cursor.execute("DELETE FROM sessions")
        cursor.execute("DELETE FROM snapshots")
        db.conn.commit()
        
        console.print("\n[green]✓[/green] All data cleared.")
        
    except Exception as e:
        console.print(f"[bold red]❌ Error:[/bold red] {e}")
        sys.exit(1)
    finally:
        close_db()


# Snapshot commands group
@cli.group()
def snapshot():
    """Manage snapshots for regression testing."""
    pass


@snapshot.command('save')
@click.argument('session_id')
@click.option('--tag', '-t', multiple=True, help='Tags for the snapshot')
def snapshot_save(session_id: str, tag: tuple):
    """
    Save a session as a snapshot for regression testing.
    """
    try:
        db = get_db()
        
        # Handle 'last'
        if session_id == 'last':
            session = db.get_latest_session()
            if not session:
                console.print("[yellow]No sessions found.[/yellow]")
                return
            session_id = session.id
        
        # Get session detail
        detail = db.get_session_detail(session_id)
        if not detail:
            console.print(f"[red]Session {session_id} not found.[/red]")
            return
        
        # Create snapshot
        from core.models import Snapshot
        
        chunks = []
        if detail.retrieval:
            chunks = [chunk.model_dump() for chunk in detail.retrieval.chunks]
        
        answer = detail.generation.response if detail.generation else ""
        
        snap = Snapshot(
            session_id=session_id,
            query=detail.session.query,
            chunks=chunks,
            answer=answer,
            cost=detail.session.total_cost or 0.0,
            tags=list(tag),
            model=detail.session.model
        )
        
        created = db.create_snapshot(snap)
        
        console.print(f"\n[green]✓[/green] Snapshot created: [cyan]{created.id}[/cyan]")
        if tag:
            console.print(f"   Tags: [yellow]{', '.join(tag)}[/yellow]")
        
    except Exception as e:
        console.print(f"[bold red]❌ Error:[/bold red] {e}")
        sys.exit(1)
    finally:
        close_db()


@snapshot.command('list')
@click.option('--limit', default=10, help='Number of snapshots to show')
def snapshot_list(limit: int):
    """List recent snapshots."""
    try:
        db = get_db()
        snapshots = db.list_snapshots(limit=limit)
        
        if not snapshots:
            console.print("[yellow]No snapshots found.[/yellow]")
            return
        
        table = Table(title=f"Snapshots (last {len(snapshots)})", box=box.ROUNDED)
        table.add_column("ID", style="cyan")
        table.add_column("Query", style="white")
        table.add_column("Tags", style="yellow")
        table.add_column("Cost", style="green", justify="right")
        table.add_column("Created", style="dim")
        
        for snap in snapshots:
            query_preview = snap.query[:40] + "..." if len(snap.query) > 40 else snap.query
            tags_str = ", ".join(snap.tags) if snap.tags else "-"
            
            table.add_row(
                snap.id[:8] + "...",
                query_preview,
                tags_str,
                format_cost(snap.cost),
                snap.timestamp.strftime("%Y-%m-%d %H:%M")
            )
        
        console.print("\n")
        console.print(table)
        
    except Exception as e:
        console.print(f"[bold red]❌ Error:[/bold red] {e}")
        sys.exit(1)
    finally:
        close_db()


def _display_session_detail(detail: SessionDetail):
    """Display session detail with rich formatting."""
    session = detail.session
    
    # Header
    console.print("\n")
    console.print(Panel(
        f"[bold]{session.query}[/bold]",
        title="[blue]Query[/blue]",
        border_style="blue"
    ))
    
    # Metadata
    meta_table = Table(show_header=False, box=None, padding=(0, 2))
    meta_table.add_column("Key", style="dim")
    meta_table.add_column("Value", style="cyan")
    
    meta_table.add_row("Session ID", session.id)
    meta_table.add_row("Model", session.model or "-")
    if session.total_cost:
        meta_table.add_row("Total Cost", format_cost(session.total_cost))
    if session.total_duration_ms:
        meta_table.add_row("Total Duration", f"{session.total_duration_ms}ms")
    meta_table.add_row("Created", session.created_at.strftime("%Y-%m-%d %H:%M:%S"))
    
    console.print(meta_table)
    console.print()
    
    # Retrieval
    if detail.retrieval:
        console.print(f"\n[bold blue]📄 RETRIEVAL[/bold blue] ({detail.retrieval.duration_ms}ms, {format_cost(detail.retrieval.embedding_cost)})")
        console.print(f"   Retrieved {len(detail.retrieval.chunks)} chunks")
        
        for i, chunk in enumerate(detail.retrieval.chunks, 1):
            score_color = "green" if chunk.metadata.score > 0.8 else "yellow" if chunk.metadata.score > 0.6 else "red"
            console.print(f"\n   [{score_color}]Chunk {i}[/{score_color}] (score: {chunk.metadata.score:.3f})")
            if chunk.metadata.source:
                console.print(f"   [dim]Source: {chunk.metadata.source}[/dim]")
            
            preview = chunk.text[:150] + "..." if len(chunk.text) > 150 else chunk.text
            console.print(f"   {preview}")
    
    # Prompt
    if detail.prompt:
        console.print(f"\n[bold yellow]📝 PROMPT[/bold yellow] ({detail.prompt.token_count} tokens)")
        
        # Show prompt in a syntax-highlighted panel
        syntax = Syntax(detail.prompt.prompt, "text", theme="monokai", line_numbers=False)
        console.print(Panel(syntax, border_style="yellow", expand=False))
    
    # Generation
    if detail.generation:
        console.print(f"\n[bold green]🤖 GENERATION[/bold green] ({detail.generation.duration_ms}ms, {format_cost(detail.generation.cost)})")
        console.print(f"   Tokens: {detail.generation.input_tokens} in → {detail.generation.output_tokens} out")
        console.print(f"\n   [bold]Response:[/bold]")
        console.print(f"   {detail.generation.response}")
    
    # Cost breakdown
    if detail.cost_breakdown:
        console.print(f"\n[bold magenta]💰 COST BREAKDOWN[/bold magenta]")
        cost_table = Table(show_header=False, box=None, padding=(0, 2))
        cost_table.add_column("Item", style="dim")
        cost_table.add_column("Cost", style="green", justify="right")
        
        cost_table.add_row("Embedding", format_cost(detail.cost_breakdown.embedding_cost))
        cost_table.add_row("Input tokens", format_cost(detail.cost_breakdown.input_cost))
        cost_table.add_row("Output tokens", format_cost(detail.cost_breakdown.output_cost))
        cost_table.add_row("[bold]Total[/bold]", f"[bold]{format_cost(detail.cost_breakdown.total_cost)}[/bold]")
        
        console.print(cost_table)
    
    console.print()


if __name__ == "__main__":
    cli()
