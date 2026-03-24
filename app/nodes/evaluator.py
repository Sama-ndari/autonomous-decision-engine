"""
Evaluator Node.

Quality gate that assesses work output and determines if the task
was completed successfully, needs retry, or requires escalation.
"""

from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.config import get_config
from app.state.schema import ADEState, EvaluationOutput, DecisionRecord
from app.state.enums import DecisionType, EvaluationResult


EVALUATOR_PROMPT = """You are a quality evaluator for an AI decision engine.

Your job is to assess the quality of work output and determine next steps.

EVALUATION CRITERIA:

1. Completeness: Does the output address all aspects of the task?
2. Accuracy: Is the information correct and well-sourced?
3. Clarity: Is the output clear and well-organized?
4. Safety: Does the output avoid harmful content or actions?
5. Relevance: Does the output stay focused on the task?

SCORING (0.0 to 1.0):
- 0.9-1.0: Excellent, no issues
- 0.7-0.9: Good, minor improvements possible
- 0.5-0.7: Acceptable, some issues to address
- 0.3-0.5: Below expectations, significant issues
- 0.0-0.3: Unacceptable, major problems

DECISION GUIDE:
- PASS (score >= 0.7): Work is acceptable, proceed to completion
- RETRY (0.4 <= score < 0.7): Work needs improvement, try again
- ESCALATE (score < 0.4 OR critical issues): Escalate to human review

AUTOMATIC ESCALATION TRIGGERS:
- Factual claims that cannot be verified
- Potential safety or ethical issues
- Signs of hallucination or fabrication
- Request misunderstanding
"""


def evaluator(state: ADEState) -> dict:
    """
    Evaluate work output quality and determine next steps.
    
    Pure function: takes state, returns state updates.
    """
    config = get_config()
    
    # Check retry limit
    if state["retry_count"] >= state["max_retries"]:
        # Force escalation after max retries
        evaluation = EvaluationOutput(
            result=EvaluationResult.ESCALATE,
            quality_score=0.3,
            feedback="Maximum retry attempts reached. Escalating to human review.",
            issues=["Max retries exceeded"],
        )
        
        record = DecisionRecord(
            timestamp=datetime.now(),
            node="evaluator",
            decision=DecisionType.HUMAN,
            reasoning="Max retries exceeded, escalating to human",
        )
        
        return {
            "evaluation": evaluation,
            "decision": DecisionType.HUMAN,
            "awaiting_human": True,
            "decision_path": [record],
        }
    
    llm = ChatOpenAI(
        model=config.model.name,
        temperature=config.model.temperature,
    ).with_structured_output(EvaluationOutput)
    
    context = f"""
Original Task: {state['task_input']}

Task Analysis:
- Domain: {state['task_analysis'].domain.value}
- Complexity: {state['task_analysis'].complexity}

Work Output:
{state['work_output']}

Attempt Number: {state['retry_count'] + 1} of {state['max_retries']}
"""
    
    messages = [
        SystemMessage(content=EVALUATOR_PROMPT),
        HumanMessage(content=f"Evaluate this work:\n{context}"),
    ]
    
    evaluation: EvaluationOutput = llm.invoke(messages)
    
    # Determine next decision based on evaluation
    if evaluation.result == EvaluationResult.PASS:
        next_decision = state["decision"]  # Keep current decision
        awaiting = False
    elif evaluation.result == EvaluationResult.RETRY:
        next_decision = state["decision"]  # Keep current decision for retry
        awaiting = False
    else:  # ESCALATE
        next_decision = DecisionType.HUMAN
        awaiting = True
    
    # Update retry count if retrying
    new_retry_count = state["retry_count"]
    if evaluation.result == EvaluationResult.RETRY:
        new_retry_count += 1
    
    record = DecisionRecord(
        timestamp=datetime.now(),
        node="evaluator",
        decision=next_decision,
        reasoning=f"Quality score: {evaluation.quality_score:.2f}, "
                  f"result: {evaluation.result.value}",
    )
    
    return {
        "evaluation": evaluation,
        "retry_count": new_retry_count,
        "awaiting_human": awaiting,
        "decision_path": [record],
    }

