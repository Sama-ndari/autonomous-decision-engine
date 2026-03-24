"""
LangGraph State schema for the Autonomous Decision Engine.

Defines the core state structure, task analysis models,
and risk assessment outputs using Pydantic.
"""

from datetime import datetime
from typing import Annotated, Any
from pydantic import BaseModel, Field
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages

from app.state.enums import DecisionType, RiskCategory, TaskDomain, EvaluationResult


# ============================================================================
# Structured Output Models (for LLM responses)
# ============================================================================

class TaskAnalysis(BaseModel):
    """Structured output from the task analyzer node."""
    
    domain: TaskDomain = Field(
        description="The primary domain of the task"
    )
    summary: str = Field(
        description="Brief summary of what the task requires"
    )
    complexity: str = Field(
        description="Complexity level: simple, moderate, or complex"
    )
    ambiguity: str = Field(
        description="Ambiguity level: clear, somewhat_ambiguous, or highly_ambiguous"
    )
    requires_authentication: bool = Field(
        description="Whether the task requires logging into a service"
    )
    requires_external_action: bool = Field(
        description="Whether the task requires actions outside the AI system"
    )
    keywords: list[str] = Field(
        default_factory=list,
        description="Key terms extracted from the task"
    )


class RiskScore(BaseModel):
    """Individual risk category score."""
    
    category: RiskCategory = Field(description="The risk category")
    score: float = Field(ge=0.0, le=1.0, description="Risk score from 0.0 to 1.0")
    reasoning: str = Field(description="Brief explanation for this score")


class RiskAssessment(BaseModel):
    """Structured output from the risk evaluator node."""
    
    scores: list[RiskScore] = Field(
        description="Individual risk scores by category"
    )
    overall_risk: float = Field(
        ge=0.0, le=1.0,
        description="Aggregate risk score from 0.0 to 1.0"
    )
    recommended_decision: DecisionType = Field(
        description="Recommended decision based on risk assessment"
    )
    reasoning: str = Field(
        description="Overall reasoning for the risk assessment"
    )
    flags: list[str] = Field(
        default_factory=list,
        description="Specific risk flags raised"
    )


class EvaluationOutput(BaseModel):
    """Structured output from the evaluator node."""
    
    result: EvaluationResult = Field(
        description="Evaluation result: pass, retry, or escalate"
    )
    quality_score: float = Field(
        ge=0.0, le=1.0,
        description="Quality score of the work output"
    )
    feedback: str = Field(
        description="Feedback on the work output"
    )
    issues: list[str] = Field(
        default_factory=list,
        description="Specific issues found"
    )


class DecisionRecord(BaseModel):
    """
    Record of a decision made during execution.
    
    Provides a complete audit trail of the decision-making process.
    """
    
    timestamp: datetime = Field(default_factory=datetime.now)
    node: str = Field(description="Node that made this decision")
    decision: DecisionType = Field(description="Decision made")
    reasoning: str = Field(description="Why this decision was made")
    risk_score: float | None = Field(default=None, description="Risk score at decision time")
    human_approved: bool | None = Field(default=None, description="Whether human approved")


# ============================================================================
# LangGraph State Definition
# ============================================================================

class ADEState(TypedDict):
    """
    Main state for the Autonomous Decision Engine graph.
    
    This TypedDict defines all state that flows through the graph.
    Each node reads from and writes to this state.
    """
    
    # === Input ===
    task_input: str  # Original user request
    
    # === Analysis ===
    task_analysis: TaskAnalysis | None  # Output from task_analyzer
    risk_assessment: RiskAssessment | None  # Output from risk_evaluator
    
    # === Decision ===
    decision: DecisionType | None  # Current routing decision
    
    # === Execution ===
    messages: Annotated[list[Any], add_messages]  # Conversation history
    work_output: str | None  # Output from worker node
    
    # === Evaluation ===
    evaluation: EvaluationOutput | None  # Output from evaluator
    retry_count: int  # Number of retry attempts
    max_retries: int  # Maximum allowed retries
    
    # === Human Input ===
    human_response: str | None  # Response from human
    awaiting_human: bool  # Whether waiting for human input
    
    # === Refusal ===
    refusal_reason: str | None  # Reason for refusal if decision is STOP
    
    # === Audit ===
    decision_path: list[DecisionRecord]  # Audit trail of all decisions
    
    # === Session ===
    thread_id: str | None  # Session identifier for checkpointing


def create_initial_state(task_input: str, thread_id: str | None = None) -> ADEState:
    """Create a fresh initial state for a new task."""
    return ADEState(
        task_input=task_input,
        task_analysis=None,
        risk_assessment=None,
        decision=None,
        messages=[],
        work_output=None,
        evaluation=None,
        retry_count=0,
        max_retries=3,
        human_response=None,
        awaiting_human=False,
        refusal_reason=None,
        decision_path=[],
        thread_id=thread_id,
    )

