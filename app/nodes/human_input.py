"""
Human Input Node.

Pauses execution and requests human confirmation or input.
This is the key safety mechanism for high-risk tasks.
"""

from datetime import datetime

from app.state.schema import ADEState, DecisionRecord
from app.state.enums import DecisionType, TaskDomain


def format_human_prompt(state: ADEState) -> str:
    """Generate a clear prompt for human review."""
    
    analysis = state["task_analysis"]
    risk = state["risk_assessment"]
    
    sections = []
    
    # Header
    sections.append("=" * 60)
    sections.append("HUMAN REVIEW REQUIRED")
    sections.append("=" * 60)
    
    # Task summary
    sections.append(f"\n📋 TASK: {state['task_input']}\n")
    
    # Analysis
    sections.append("📊 ANALYSIS:")
    sections.append(f"   Domain: {analysis.domain.value}")
    sections.append(f"   Complexity: {analysis.complexity}")
    sections.append(f"   Ambiguity: {analysis.ambiguity}")
    
    # Risk assessment
    if risk:
        sections.append(f"\n⚠️  RISK ASSESSMENT:")
        sections.append(f"   Overall Risk: {risk.overall_risk:.0%}")
        sections.append(f"   Reasoning: {risk.reasoning}")
        if risk.flags:
            sections.append(f"   Flags: {', '.join(risk.flags)}")
    
    # Work output if exists
    if state.get("work_output"):
        sections.append(f"\n📝 WORK OUTPUT (for review):")
        sections.append("-" * 40)
        sections.append(state["work_output"])
        sections.append("-" * 40)
    
    # Evaluation if exists
    if state.get("evaluation"):
        eval_out = state["evaluation"]
        sections.append(f"\n🔍 EVALUATION:")
        sections.append(f"   Quality: {eval_out.quality_score:.0%}")
        sections.append(f"   Feedback: {eval_out.feedback}")
        if eval_out.issues:
            sections.append(f"   Issues: {', '.join(eval_out.issues)}")
    
    # Decision path summary
    if state.get("decision_path"):
        sections.append(f"\n📜 DECISION PATH:")
        for record in state["decision_path"][-5:]:  # Last 5 decisions
            sections.append(f"   [{record.node}] {record.decision.value}: {record.reasoning[:50]}...")
    
    # Instructions
    sections.append("\n" + "=" * 60)
    sections.append("OPTIONS:")
    sections.append("  [approve]  - Approve and proceed with the task")
    sections.append("  [modify]   - Provide guidance and retry")
    sections.append("  [reject]   - Reject and stop execution")
    sections.append("=" * 60)
    
    return "\n".join(sections)


def human_input(state: ADEState) -> dict:
    """
    Prepare state for human input.
    
    This node sets up the state for human review.
    Actual input collection happens in the CLI layer.
    
    Pure function: takes state, returns state updates.
    """
    record = DecisionRecord(
        timestamp=datetime.now(),
        node="human_input",
        decision=DecisionType.HUMAN,
        reasoning="Awaiting human confirmation or guidance",
    )
    
    return {
        "awaiting_human": True,
        "decision_path": [record],
    }


def process_human_response(state: ADEState, response: str, action: str) -> dict:
    """
    Process the human's response and update state accordingly.
    
    Args:
        state: Current state
        response: Human's text response
        action: One of 'approve', 'modify', 'reject'
    
    Returns:
        State updates based on human decision
    """
    
    if action == "approve":
        record = DecisionRecord(
            timestamp=datetime.now(),
            node="human_input",
            decision=state["decision"] or DecisionType.HUMAN,
            reasoning="Human approved the action",
            human_approved=True,
        )
        
        return {
            "awaiting_human": False,
            "human_response": response or "Approved",
            "decision_path": [record],
        }
    
    elif action == "modify":
        record = DecisionRecord(
            timestamp=datetime.now(),
            node="human_input",
            decision=DecisionType.HUMAN,
            reasoning=f"Human requested modification: {response[:50]}...",
            human_approved=None,  # Pending re-evaluation
        )
        
        return {
            "awaiting_human": False,
            "human_response": response,
            "retry_count": 0,  # Reset retries with new guidance
            "decision_path": [record],
        }
    
    else:  # reject
        record = DecisionRecord(
            timestamp=datetime.now(),
            node="human_input",
            decision=DecisionType.STOP,
            reasoning=f"Human rejected: {response or 'No reason provided'}",
            human_approved=False,
        )
        
        return {
            "awaiting_human": False,
            "decision": DecisionType.STOP,
            "refusal_reason": f"Rejected by human: {response or 'No reason provided'}",
            "decision_path": [record],
        }

