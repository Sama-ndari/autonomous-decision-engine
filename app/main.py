#!/usr/bin/env python3
"""
Autonomous Decision Engine - Main Entry Point

A Human-in-the-Loop AI Decision System that decides whether to:
- Act autonomously
- Use tools with oversight
- Request human confirmation
- Refuse to proceed

Usage:
    python -m app.main                    # Interactive mode
    python -m app.main "Your task here"   # Single task mode
    python -m app.main --help             # Show help
"""

import sys
import asyncio
import argparse

from app.ui.cli import run_interactive_session, run_task, print_result, console


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Autonomous Decision Engine - Human-in-the-Loop AI Decision System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m app.main
      Start interactive mode
  
  python -m app.main "Research Campus France scholarship requirements"
      Run a single task
  
  python -m app.main --thread-id my-session "Continue my application"
      Continue an existing session
"""
    )
    
    parser.add_argument(
        "task",
        nargs="?",
        help="Task to execute (if not provided, starts interactive mode)"
    )
    
    parser.add_argument(
        "--thread-id", "-t",
        help="Thread ID for session continuity"
    )
    
    parser.add_argument(
        "--no-memory",
        action="store_true",
        help="Disable checkpointing (no persistence)"
    )
    
    parser.add_argument(
        "--version", "-v",
        action="version",
        version="%(prog)s 0.1.0"
    )
    
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    
    try:
        if args.task:
            # Single task mode
            result = asyncio.run(run_task(args.task, args.thread_id))
            print_result(result)
        else:
            # Interactive mode
            run_interactive_session()
    
    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted. Goodbye![/dim]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[bold red]Fatal Error:[/bold red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

