"""
Checkpointing and Memory Persistence.

Provides in-memory checkpointing for LangGraph sessions.
MemorySaver is used for async compatibility with graph.ainvoke().
Note: Sessions don't persist across restarts.
"""

from langgraph.checkpoint.memory import MemorySaver


# Global checkpointer instance
_checkpointer: MemorySaver | None = None


def get_checkpointer() -> MemorySaver:
    """
    Get the global checkpointer instance.
    
    Uses MemorySaver for full async compatibility with graph.ainvoke().
    Note: Sessions don't persist across app restarts.
    
    Returns:
        MemorySaver instance for LangGraph
    """
    global _checkpointer
    
    if _checkpointer is not None:
        return _checkpointer
    
    # Use MemorySaver - fully compatible with async ainvoke()
    _checkpointer = MemorySaver()
    return _checkpointer


def reset_checkpointer():
    """Reset the global checkpointer (useful for testing)."""
    global _checkpointer
    _checkpointer = None


def get_thread_config(thread_id: str) -> dict:
    """
    Get LangGraph config dict for a specific thread.
    
    Args:
        thread_id: Unique identifier for the conversation thread
    
    Returns:
        Config dict for LangGraph invocation
    """
    return {
        "configurable": {
            "thread_id": thread_id,
        }
    }

