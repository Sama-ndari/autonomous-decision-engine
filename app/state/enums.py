"""
Decision enums for the Autonomous Decision Engine.

Defines the core decision types, risk categories, and task domains.
"""

from enum import Enum


class DecisionType(str, Enum):
    """
    Core decision types for AI autonomy routing.
    
    AUTONOMOUS: Full autonomy - AI proceeds without human intervention
    TOOLS: Tool-assisted - AI uses tools with oversight
    HUMAN: Human-in-the-loop - Requires explicit human confirmation
    STOP: Refusal - AI refuses to proceed due to safety/ethics
    """
    AUTONOMOUS = "autonomous"
    TOOLS = "tools"
    HUMAN = "human"
    STOP = "stop"


class RiskCategory(str, Enum):
    """
    Risk categories evaluated during decision-making.
    
    Each category is assessed independently and combined
    to determine the overall risk level.
    """
    LEGAL = "legal"           # Contracts, visas, official documents
    FINANCIAL = "financial"   # Payments, scholarships, investments
    ETHICAL = "ethical"       # Privacy, consent, discrimination
    HALLUCINATION = "hallucination"  # Factual claims requiring verification
    AUTHENTICATION = "authentication"  # Login-protected workflows
    IRREVERSIBLE = "irreversible"  # Actions that cannot be undone


class TaskDomain(str, Enum):
    """
    Task domain categories for specialized handling.
    
    Some domains have specific workflows and default
    risk levels (e.g., Campus France defaults to HUMAN).
    """
    GENERAL = "general"
    RESEARCH = "research"
    WRITING = "writing"
    CODING = "coding"
    CAMPUS_FRANCE = "campus_france"
    VISA = "visa"
    SCHOLARSHIP = "scholarship"
    LEGAL = "legal"
    FINANCIAL = "financial"
    MEDICAL = "medical"


class EvaluationResult(str, Enum):
    """
    Results from the quality evaluation gate.
    
    PASS: Task completed successfully
    RETRY: Task needs another attempt
    ESCALATE: Task should be escalated to human
    """
    PASS = "pass"
    RETRY = "retry"
    ESCALATE = "escalate"


# Domains that require human-in-the-loop by default
HIGH_RISK_DOMAINS = frozenset({
    TaskDomain.CAMPUS_FRANCE,
    TaskDomain.VISA,
    TaskDomain.SCHOLARSHIP,
    TaskDomain.LEGAL,
    TaskDomain.FINANCIAL,
    TaskDomain.MEDICAL,
})

