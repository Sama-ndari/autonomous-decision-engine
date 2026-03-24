"""
Risk Evaluator Node.

Evaluates the risk level of a task based on multiple categories
and determines the appropriate autonomy level.
"""

from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.config import get_config
from app.state.schema import ADEState, RiskAssessment, DecisionRecord
from app.state.enums import DecisionType, RiskCategory, HIGH_RISK_DOMAINS


RISK_EVALUATION_PROMPT = """You are a risk evaluator for an AI decision engine.

Your job is to assess the risks of proceeding with a task and recommend
an appropriate level of autonomy.

RISK CATEGORIES (score each 0.0 to 1.0):

1. LEGAL: Risk of legal consequences
   - High: Contracts, visa applications, legal filings
   - Medium: Official documents, formal requests
   - Low: General information

2. FINANCIAL: Risk of financial loss
   - High: Payments, investments, scholarships
   - Medium: Price comparisons, budgeting
   - Low: General financial info

3. ETHICAL: Risk of ethical violations
   - High: Privacy violations, discrimination, deception
   - Medium: Persuasive content, personal advice
   - Low: Factual, neutral content

4. HALLUCINATION: Risk of factual errors causing harm
   - High: Medical, legal, safety information
   - Medium: Technical facts, statistics
   - Low: Creative content, opinions

5. AUTHENTICATION: Risk from requiring login
   - High: Tasks requiring user credentials
   - Medium: Tasks on authenticated platforms
   - Low: Public information only

6. IRREVERSIBLE: Risk of permanent consequences
   - High: Submissions, purchases, deletions
   - Medium: Sending messages, creating accounts
   - Low: Research, drafting, planning

DECISION GUIDE:
- AUTONOMOUS (overall_risk < 0.3): Full autonomy, proceed without intervention
- TOOLS (0.3 <= overall_risk < 0.5): Use tools but maintain oversight
- HUMAN (0.5 <= overall_risk < 0.7): Require human confirmation before action
- STOP (overall_risk >= 0.7): Refuse to proceed, too risky

IMPORTANT: Tasks requiring REAL-TIME or CURRENT information should use TOOLS:
- Weather queries → TOOLS (need web search for current data)
- News queries → TOOLS (need web search for recent events)
- Stock prices, exchange rates → TOOLS (need current data)
- Sports scores → TOOLS (need live data)
- Any "what is the current..." question → TOOLS

MANDATORY OVERRIDES:
- Campus France, visa, scholarship, legal, financial, medical tasks → minimum HUMAN
- Any task requiring login → minimum HUMAN
- Any irreversible action → minimum HUMAN
"""

# Keywords that indicate real-time information is needed
REALTIME_KEYWORDS = frozenset({
    "weather", "forecast", "temperature", "rain", "sunny", "cloudy",
    "news", "latest", "current", "today", "now", "live",
    "stock price", "exchange rate", "bitcoin", "crypto",
    "score", "match", "game",
})


def needs_realtime_data(task_input: str, keywords: list[str]) -> bool:
    """Check if task requires real-time information."""
    text_lower = task_input.lower()
    all_keywords = list(keywords) + list(REALTIME_KEYWORDS)
    return any(kw in text_lower for kw in all_keywords)


def risk_evaluator(state: ADEState) -> dict:
    """
    Evaluate task risk and determine autonomy level.
    
    Pure function: takes state, returns state updates.
    """
    config = get_config()
    analysis = state["task_analysis"]
    
    # Check for mandatory HUMAN override based on domain
    forced_human = analysis.domain in HIGH_RISK_DOMAINS
    
    # Check if task needs real-time data (should use TOOLS)
    needs_tools = needs_realtime_data(state["task_input"], analysis.keywords)
    
    llm = ChatOpenAI(
        model=config.model.name,
        temperature=config.model.temperature,
    ).with_structured_output(RiskAssessment)
    
    task_context = f"""
Task: {state['task_input']}

Analysis:
- Domain: {analysis.domain.value}
- Complexity: {analysis.complexity}
- Ambiguity: {analysis.ambiguity}
- Requires Authentication: {analysis.requires_authentication}
- Requires External Action: {analysis.requires_external_action}
- Keywords: {', '.join(analysis.keywords)}
"""
    
    messages = [
        SystemMessage(content=RISK_EVALUATION_PROMPT),
        HumanMessage(content=f"Evaluate the risk of this task:\n{task_context}"),
    ]
    
    assessment: RiskAssessment = llm.invoke(messages)
    
    # Apply mandatory overrides
    final_decision = assessment.recommended_decision
    override_reason = None
    
    # Override: Real-time queries need TOOLS
    if needs_tools and final_decision == DecisionType.AUTONOMOUS:
        final_decision = DecisionType.TOOLS
        override_reason = "Task requires real-time data - using web search tools"
    
    # Override: High-risk domains need HUMAN
    if forced_human and final_decision in (DecisionType.AUTONOMOUS, DecisionType.TOOLS):
        final_decision = DecisionType.HUMAN
        override_reason = f"Domain '{analysis.domain.value}' requires human-in-the-loop"
    
    # Override: Authentication needs HUMAN
    if analysis.requires_authentication and final_decision in (DecisionType.AUTONOMOUS, DecisionType.TOOLS):
        final_decision = DecisionType.HUMAN
        override_reason = "Task requires authentication - human must log in"
    
    # Create audit record
    reasoning = assessment.reasoning
    if override_reason:
        reasoning = f"{reasoning} [OVERRIDE: {override_reason}]"
    
    record = DecisionRecord(
        timestamp=datetime.now(),
        node="risk_evaluator",
        decision=final_decision,
        reasoning=reasoning,
        risk_score=assessment.overall_risk,
    )
    
    return {
        "risk_assessment": assessment,
        "decision": final_decision,
        "decision_path": [record],
    }

