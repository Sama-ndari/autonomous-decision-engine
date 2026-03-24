"""
Main Decision Graph for the Autonomous Decision Engine.

Assembles the complete LangGraph StateGraph with all nodes,
edges, and conditional routing.
"""

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from app.state.schema import ADEState
from app.state.enums import DecisionType
from app.nodes.task_analyzer import task_analyzer
from app.nodes.risk_evaluator import risk_evaluator
from app.nodes.worker import worker, tool_worker
from app.nodes.evaluator import evaluator
from app.nodes.human_input import human_input
from app.nodes.refusal import refusal
from app.graphs.routers import (
    route_after_risk_evaluation,
    route_after_evaluation,
    route_after_human_input,
    route_after_tools,
)
from app.memory.checkpoint import get_checkpointer


def create_decision_graph(tools: list | None = None, use_memory: bool = True):
    """
    Create and compile the decision graph.
    
    Args:
        tools: Optional list of LangChain tools for tool-assisted mode
        use_memory: Whether to use SQLite checkpointing
    
    Returns:
        Compiled LangGraph ready for execution
    """
    
    # Initialize the graph builder
    graph_builder = StateGraph(ADEState)
    
    # =========================================================================
    # Add Nodes
    # =========================================================================
    
    graph_builder.add_node("task_analyzer", task_analyzer)
    graph_builder.add_node("risk_evaluator", risk_evaluator)
    graph_builder.add_node("worker", worker)
    graph_builder.add_node("evaluator", evaluator)
    graph_builder.add_node("human_input", human_input)
    graph_builder.add_node("refusal", refusal)
    
    # Add tool nodes if tools are provided
    if tools:
        # Tool worker with bound tools
        def tool_worker_node(state: ADEState) -> dict:
            return tool_worker(state, tools)
        
        graph_builder.add_node("tool_worker", tool_worker_node)
        graph_builder.add_node("tool_executor", ToolNode(tools=tools))
    else:
        # Fallback: route TOOLS decisions to regular worker
        graph_builder.add_node("tool_worker", worker)
    
    # =========================================================================
    # Add Edges
    # =========================================================================
    
    # Start -> Task Analyzer
    graph_builder.add_edge(START, "task_analyzer")
    
    # Task Analyzer -> Risk Evaluator
    graph_builder.add_edge("task_analyzer", "risk_evaluator")
    
    # Risk Evaluator -> Conditional routing based on decision
    graph_builder.add_conditional_edges(
        "risk_evaluator",
        route_after_risk_evaluation,
        {
            "worker": "worker",
            "tool_worker": "tool_worker",
            "human_input": "human_input",
            "refusal": "refusal",
        }
    )
    
    # Worker -> Evaluator
    graph_builder.add_edge("worker", "evaluator")
    
    # Tool Worker -> Conditional (check for tool calls)
    if tools:
        graph_builder.add_conditional_edges(
            "tool_worker",
            route_after_tools,
            {
                "tool_executor": "tool_executor",
                "evaluator": "evaluator",
            }
        )
        # Tool Executor -> Tool Worker (for multi-step tool use)
        graph_builder.add_edge("tool_executor", "tool_worker")
    else:
        graph_builder.add_edge("tool_worker", "evaluator")
    
    # Evaluator -> Conditional routing based on evaluation result
    graph_builder.add_conditional_edges(
        "evaluator",
        route_after_evaluation,
        {
            "END": END,
            "worker": "worker",
            "tool_worker": "tool_worker",
            "human_input": "human_input",
        }
    )
    
    # Human Input -> Conditional routing based on human response
    graph_builder.add_conditional_edges(
        "human_input",
        route_after_human_input,
        {
            "worker": "worker",
            "tool_worker": "tool_worker",
            "task_analyzer": "task_analyzer",
            "refusal": "refusal",
            "END": END,
        }
    )
    
    # Refusal -> END
    graph_builder.add_edge("refusal", END)
    
    # =========================================================================
    # Compile with Checkpointing
    # =========================================================================
    
    if use_memory:
        checkpointer = get_checkpointer()
        graph = graph_builder.compile(checkpointer=checkpointer)
    else:
        graph = graph_builder.compile()
    
    return graph


def get_graph_mermaid(tools: list | None = None) -> str:
    """
    Generate a Mermaid diagram of the decision graph.
    
    Returns:
        Mermaid diagram string
    """
    graph = create_decision_graph(tools=tools, use_memory=False)
    return graph.get_graph().draw_mermaid()


# Pre-built graph instance for simple use cases
_default_graph = None


def get_default_graph():
    """Get the default decision graph (lazy loaded)."""
    global _default_graph
    if _default_graph is None:
        _default_graph = create_decision_graph(tools=None, use_memory=True)
    return _default_graph

