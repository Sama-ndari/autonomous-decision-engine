"""
Task Analyzer Node.

Analyzes the incoming task to determine its domain, complexity,
ambiguity, and special requirements. This is the first node in
the decision pipeline.
"""

from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.config import get_config
from app.state.schema import ADEState, TaskAnalysis, DecisionRecord
from app.state.enums import DecisionType, TaskDomain


TASK_ANALYSIS_PROMPT = """You are a task analyzer for an AI decision engine.

Your job is to analyze user requests and classify them accurately.
Be thorough but concise in your analysis.

Focus on:
1. Identifying the primary domain of the task
2. Assessing complexity (simple, moderate, complex)
3. Detecting ambiguity (clear, somewhat_ambiguous, highly_ambiguous)
4. Identifying if authentication/login is required
5. Identifying if external real-world actions are needed
6. Extracting key terms

DOMAIN CLASSIFICATION GUIDE:
- campus_france: Anything related to Campus France, French scholarships, Études en France
- visa: Visa applications, immigration, travel documents
- scholarship: Scholarships, grants, financial aid for education
- legal: Contracts, legal documents, court matters
- financial: Banking, payments, investments, taxes
- medical: Health information, medical decisions
- research: Information gathering, fact-finding
- writing: Content creation, documentation
- coding: Programming, technical implementation
- general: Everything else

Be especially careful to flag:
- Tasks requiring login to any service
- Tasks that could have irreversible consequences
- Tasks involving personal/sensitive information
"""


def task_analyzer(state: ADEState) -> dict:
    """
    Analyze the task and produce structured classification.
    
    Pure function: takes state, returns state updates.
    """
    config = get_config()
    
    llm = ChatOpenAI(
        model=config.model.name,
        temperature=config.model.temperature,
    ).with_structured_output(TaskAnalysis)
    
    messages = [
        SystemMessage(content=TASK_ANALYSIS_PROMPT),
        HumanMessage(content=f"Analyze this task:\n\n{state['task_input']}"),
    ]
    
    analysis: TaskAnalysis = llm.invoke(messages)
    
    # Create audit record
    record = DecisionRecord(
        timestamp=datetime.now(),
        node="task_analyzer",
        decision=DecisionType.AUTONOMOUS,  # Placeholder, actual decision in risk_evaluator
        reasoning=f"Task classified as {analysis.domain.value} domain, "
                  f"complexity={analysis.complexity}, ambiguity={analysis.ambiguity}",
    )
    
    return {
        "task_analysis": analysis,
        "decision_path": [record],
    }

