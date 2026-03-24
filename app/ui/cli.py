"""
Command-Line Interface for the Autonomous Decision Engine.

Provides an interactive CLI for submitting tasks, reviewing decisions,
and providing human input when required.
"""

import asyncio
import uuid
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.markdown import Markdown
from rich import print as rprint

from app.state.schema import ADEState, create_initial_state, DecisionRecord
from app.state.enums import DecisionType, EvaluationResult
from app.graphs.decision_graph import create_decision_graph
from app.nodes.human_input import format_human_prompt, process_human_response
from app.memory.checkpoint import get_thread_config
from app.tools.search import get_search_tools
from app.tools.document import get_document_tools
from app.tools.notifications import get_notification_tools, notify_human_required, notify_task_complete


console = Console()


def print_header():
    """Print the application header."""
    console.print(Panel.fit(
        "[bold blue]Autonomous Decision Engine[/bold blue]\n"
        "[dim]Human-in-the-Loop AI Decision System[/dim]",
        border_style="blue"
    ))
    console.print()


def print_decision_path(decision_path: list[DecisionRecord]):
    """Print the decision audit trail."""
    if not decision_path:
        return
    
    table = Table(title="Decision Path", show_header=True, header_style="bold magenta")
    table.add_column("Time", style="dim")
    table.add_column("Node", style="cyan")
    table.add_column("Decision", style="green")
    table.add_column("Reasoning")
    
    for record in decision_path[-10:]:  # Last 10 decisions
        table.add_row(
            record.timestamp.strftime("%H:%M:%S"),
            record.node,
            record.decision.value,
            record.reasoning[:50] + "..." if len(record.reasoning) > 50 else record.reasoning
        )
    
    console.print(table)
    console.print()


def print_result(state: ADEState):
    """Print the final result."""
    console.print("\n" + "=" * 60)
    
    decision = state.get("decision")
    if decision == DecisionType.STOP:
        console.print("[bold red]TASK REFUSED[/bold red]")
        if state.get("refusal_reason"):
            console.print(f"Reason: {state['refusal_reason']}")
    else:
        console.print("[bold green]TASK COMPLETED[/bold green]")
    
    console.print("=" * 60 + "\n")
    
    # Print work output
    if state.get("work_output"):
        console.print(Panel(
            Markdown(state["work_output"]),
            title="Output",
            border_style="green" if decision != DecisionType.STOP else "red"
        ))
    
    # Print decision path
    print_decision_path(state.get("decision_path", []))


def get_human_input(state: ADEState) -> tuple[str, str]:
    """
    Get human input when required.
    
    Returns:
        Tuple of (response_text, action)
    """
    # Print the human review prompt
    prompt = format_human_prompt(state)
    console.print(Panel(prompt, title="[bold yellow]Human Review Required[/bold yellow]", border_style="yellow"))
    
    # Get action
    console.print("\n[bold]Choose an action:[/bold]")
    console.print("  [green]1)[/green] Approve - Proceed with the task")
    console.print("  [yellow]2)[/yellow] Modify - Provide guidance and retry")
    console.print("  [red]3)[/red] Reject - Stop execution")
    
    choice = Prompt.ask(
        "Your choice",
        choices=["1", "2", "3", "approve", "modify", "reject"],
        default="1"
    )
    
    action_map = {
        "1": "approve",
        "2": "modify", 
        "3": "reject",
        "approve": "approve",
        "modify": "modify",
        "reject": "reject",
    }
    action = action_map[choice]
    
    # Get response text for modify/reject
    response = ""
    if action == "modify":
        response = Prompt.ask("Your guidance")
    elif action == "reject":
        response = Prompt.ask("Reason for rejection (optional)", default="")
    
    return response, action


async def run_task(task_input: str, thread_id: Optional[str] = None) -> ADEState:
    """
    Run a task through the decision engine.
    
    Args:
        task_input: The user's task description
        thread_id: Optional thread ID for session continuity
    
    Returns:
        Final state after execution
    """
    if not thread_id:
        thread_id = str(uuid.uuid4())
    
    console.print(f"\n[dim]Session: {thread_id}[/dim]")
    console.print(f"[bold]Task:[/bold] {task_input}\n")
    
    # Create graph with tools
    tools = get_search_tools() + get_document_tools() + get_notification_tools()
    graph = create_decision_graph(tools=tools, use_memory=True)
    
    # Create initial state
    state = create_initial_state(task_input, thread_id)
    config = get_thread_config(thread_id)
    
    # Run the graph with human-in-the-loop handling
    with console.status("[bold blue]Processing...[/bold blue]"):
        result = await graph.ainvoke(state, config=config)
    
    # Check if human input is needed
    while result.get("awaiting_human"):
        # Send push notification that human input is required
        notify_human_required(task_input[:50])
        
        response, action = get_human_input(result)
        
        # Process human response
        updates = process_human_response(result, response, action)
        
        # Update state and continue
        for key, value in updates.items():
            result[key] = value
        
        # Continue execution if not rejected
        if result.get("decision") != DecisionType.STOP:
            with console.status("[bold blue]Continuing...[/bold blue]"):
                result = await graph.ainvoke(result, config=config)
        else:
            break
    
    # Send completion notification
    decision = result.get("decision")
    if decision:
        notify_task_complete(task_input[:50], decision.value)
    
    return result


def run_interactive_session():
    """Run an interactive CLI session."""
    print_header()
    
    console.print("[dim]Type 'quit' or 'exit' to end the session.[/dim]")
    console.print("[dim]Type 'history' to see the decision path.[/dim]")
    console.print("[dim]Type 'reset' to start a new conversation.[/dim]")
    console.print()
    
    thread_id = str(uuid.uuid4())
    history: list[ADEState] = []
    conversation_context: list[tuple[str, str]] = []  # List of (user_input, ai_response)
    
    while True:
        try:
            task_input = Prompt.ask("[bold cyan]Task[/bold cyan]")
            
            if task_input.lower() in ("quit", "exit", "q"):
                console.print("\n[dim]Goodbye![/dim]")
                break
            
            if task_input.lower() == "reset":
                thread_id = str(uuid.uuid4())
                history = []
                conversation_context = []
                console.print("[dim]Conversation reset. Starting fresh.[/dim]\n")
                continue
            
            if task_input.lower() == "history":
                if history:
                    for i, state in enumerate(history, 1):
                        console.print(f"\n[bold]Task {i}:[/bold] {state['task_input']}")
                        print_decision_path(state.get("decision_path", []))
                else:
                    console.print("[dim]No history yet.[/dim]")
                continue
            
            if not task_input.strip():
                continue
            
            # Build context-aware task input
            if conversation_context:
                context_str = "\n".join([
                    f"User: {u}\nAssistant: {a}" 
                    for u, a in conversation_context[-3:]  # Last 3 exchanges
                ])
                full_task = f"Previous conversation:\n{context_str}\n\nNew user message: {task_input}"
            else:
                full_task = task_input
            
            # Run the task with context
            result = asyncio.run(run_task(full_task, thread_id))
            history.append(result)
            
            # Save to conversation context
            ai_response = result.get("work_output", "")[:200] if result.get("work_output") else ""
            conversation_context.append((task_input, ai_response))
            
            # Print result
            print_result(result)
            
        except KeyboardInterrupt:
            console.print("\n\n[dim]Interrupted. Goodbye![/dim]")
            break
        except Exception as e:
            console.print(f"\n[bold red]Error:[/bold red] {e}")
            console.print("[dim]Please try again.[/dim]\n")


def main():
    """Main entry point for the CLI."""
    run_interactive_session()


if __name__ == "__main__":
    main()

