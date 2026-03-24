"""
Routing Logic for the Decision Graph.

Contains all conditional routing functions used by the StateGraph
to determine which node to execute next.
"""

from app.state.schema import ADEState
from app.state.enums import DecisionType, EvaluationResult


def route_after_risk_evaluation(state: ADEState) -> str:
    """
    Route based on the risk evaluator's decision.
    
    Returns the name of the next node to execute.
    """
    decision = state.get("decision")
    
    if decision == DecisionType.AUTONOMOUS:
        return "worker"
    elif decision == DecisionType.TOOLS:
        return "tool_worker"
    elif decision == DecisionType.HUMAN:
        return "human_input"
    elif decision == DecisionType.STOP:
        return "refusal"
    else:
        # Default to human for safety if decision is unclear
        return "human_input"


def route_after_evaluation(state: ADEState) -> str:
    """
    Route based on the evaluator's quality assessment.
    
    Returns the name of the next node or END.
    """
    evaluation = state.get("evaluation")
    
    if not evaluation:
        # No evaluation yet, should not happen but handle gracefully
        return "evaluator"
    
    if evaluation.result == EvaluationResult.PASS:
        return "END"
    elif evaluation.result == EvaluationResult.RETRY:
        decision = state.get("decision")
        return "tool_worker" if decision == DecisionType.TOOLS else "worker"
    else:  # ESCALATE
        return "human_input"


def route_after_human_input(state: ADEState) -> str:
    """
    Route after human provides input.
    
    Returns the name of the next node based on human's action.
    """
    decision = state.get("decision")
    
    # If human rejected (decision changed to STOP)
    if decision == DecisionType.STOP:
        return "refusal"
    
    # If still waiting for human input, END the graph so CLI can handle it
    if state.get("awaiting_human") and not state.get("human_response"):
        return "END"
    
    # If human approved and we have work output, go to end
    if state.get("work_output") and not state.get("awaiting_human"):
        return "END"
    
    # If human provided guidance, re-analyze with new context
    if state.get("human_response"):
        # Go back to worker with human guidance
        if state.get("decision") == DecisionType.TOOLS:
            return "tool_worker"
        return "worker"
    
    # Default: analyze again
    return "task_analyzer"


def route_after_tools(state: ADEState) -> str:
    """
    Route after tool execution.
    
    Checks if the last message has tool calls that need processing.
    """
    messages = state.get("messages", [])
    
    if not messages:
        return "evaluator"
    
    last_message = messages[-1]
    has_tool_calls = hasattr(last_message, "tool_calls") and last_message.tool_calls
    
    if has_tool_calls:
        return "tool_executor"
    
    return "evaluator"


def should_continue_tools(state: ADEState) -> bool:
    """
    Check if tool execution should continue.
    
    Returns True if there are pending tool calls.
    """
    messages = state.get("messages", [])
    
    if not messages:
        return False
    
    last_message = messages[-1]
    return hasattr(last_message, "tool_calls") and bool(last_message.tool_calls)

