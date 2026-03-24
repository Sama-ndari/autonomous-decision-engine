"""
Campus France Workflow.

Domain-specific logic for handling Campus France scholarship applications
and related tasks. This workflow enforces strict safety constraints:

- No credential storage
- Human must log in manually
- Explicit confirmation before any submission
- Read-only access to public pages by default
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from app.state.schema import ADEState, TaskAnalysis
from app.state.enums import DecisionType, TaskDomain


class CampusFranceStep(str, Enum):
    """Steps in the Campus France application process."""
    
    RESEARCH = "research"                    # Gathering information
    REQUIREMENTS = "requirements"            # Understanding requirements
    CV_PREPARATION = "cv_preparation"        # Preparing CV
    MOTIVATION_LETTER = "motivation_letter"  # Writing motivation letter
    STUDY_PROJECT = "study_project"          # Writing study project
    DOCUMENT_COLLECTION = "document_collection"  # Gathering documents
    HUMAN_LOGIN = "human_login"              # Human logs into portal
    FORM_REVIEW = "form_review"              # Reviewing forms before submission
    SUBMISSION = "submission"                # Final submission (human only)


@dataclass
class CampusFranceContext:
    """Context for Campus France workflow."""
    
    current_step: CampusFranceStep
    program_name: Optional[str] = None
    school_name: Optional[str] = None
    deadline: Optional[str] = None
    requirements_gathered: bool = False
    cv_prepared: bool = False
    motivation_letter_prepared: bool = False
    study_project_prepared: bool = False
    human_logged_in: bool = False


# Keywords that indicate Campus France related tasks
CAMPUS_FRANCE_KEYWORDS = frozenset({
    "campus france",
    "campusfrance",
    "études en france",
    "etudes en france",
    "study in france",
    "french scholarship",
    "bourse france",
    "eiffel",
    "pastel",
    "hors dap",
    "dap",
    "etudes-en-france.fr",
})


def is_campus_france_task(task_input: str) -> bool:
    """
    Detect if a task is related to Campus France.
    
    Args:
        task_input: The user's task description
    
    Returns:
        True if the task appears to be Campus France related
    """
    task_lower = task_input.lower()
    return any(keyword in task_lower for keyword in CAMPUS_FRANCE_KEYWORDS)


def detect_campus_france_step(task_input: str) -> CampusFranceStep:
    """
    Detect which step of the Campus France process this task relates to.
    
    Args:
        task_input: The user's task description
    
    Returns:
        The detected step
    """
    task_lower = task_input.lower()
    
    # Check for specific steps
    if any(word in task_lower for word in ["login", "log in", "sign in", "portal"]):
        return CampusFranceStep.HUMAN_LOGIN
    
    if any(word in task_lower for word in ["submit", "send", "finalize"]):
        return CampusFranceStep.SUBMISSION
    
    if any(word in task_lower for word in ["cv", "resume", "curriculum"]):
        return CampusFranceStep.CV_PREPARATION
    
    if any(word in task_lower for word in ["motivation", "lettre", "cover letter"]):
        return CampusFranceStep.MOTIVATION_LETTER
    
    if any(word in task_lower for word in ["study project", "projet", "project"]):
        return CampusFranceStep.STUDY_PROJECT
    
    if any(word in task_lower for word in ["requirement", "document", "need"]):
        return CampusFranceStep.REQUIREMENTS
    
    if any(word in task_lower for word in ["review", "check", "verify"]):
        return CampusFranceStep.FORM_REVIEW
    
    # Default to research
    return CampusFranceStep.RESEARCH


def get_step_guidance(step: CampusFranceStep) -> str:
    """
    Get guidance for a specific Campus France step.
    
    Args:
        step: The current step
    
    Returns:
        Guidance text for the user
    """
    guidance = {
        CampusFranceStep.RESEARCH: """
## Campus France Research Phase

I can help you:
- Find information about programs and schools
- Understand eligibility criteria
- Research scholarship options (Eiffel, regional, school-specific)
- Find application deadlines

**What I need from you:**
- Your field of study
- Desired degree level (Bachelor's, Master's, PhD)
- Any specific schools or regions of interest
""",
        
        CampusFranceStep.REQUIREMENTS: """
## Campus France Requirements

For most Campus France applications, you'll need:

**Mandatory Documents:**
1. Valid passport
2. Academic transcripts (translated to French)
3. Diplomas/certificates (translated)
4. CV (French format)
5. Motivation letter
6. Study project (Projet d'études)
7. Language certificates (French B2/C1 or English depending on program)

**May Also Need:**
- Recommendation letters
- Portfolio (for art/design programs)
- Research proposal (for PhD)
- Proof of financial resources

I can help you understand specific requirements for your target program.
""",
        
        CampusFranceStep.CV_PREPARATION: """
## CV Preparation (French Format)

I can help you create a French-style CV including:
- Proper structure and sections
- French conventions (photo, personal details)
- Academic-focused formatting
- Translation considerations

**Important:** I'll provide guidance and draft content, but you should 
review and personalize everything before use.
""",
        
        CampusFranceStep.MOTIVATION_LETTER: """
## Motivation Letter Preparation

I can help you write a compelling motivation letter:
- Proper French formal letter structure
- Key points to address
- How to connect your background to goals
- Formal closing formulas

**Important:** The letter should be authentic and personal. I'll help 
with structure and language, but the content should be genuinely yours.
""",
        
        CampusFranceStep.STUDY_PROJECT: """
## Study Project (Projet d'Études)

I can help you create your study project:
- Structure and flow
- How to present your academic journey
- Connecting past studies to future goals
- Why France, why this program

**Important:** This document is crucial for your application. 
Be honest and coherent in your narrative.
""",
        
        CampusFranceStep.DOCUMENT_COLLECTION: """
## Document Collection Checklist

I can help you:
- Create a checklist of required documents
- Understand translation requirements
- Track your document collection progress
- Identify missing items

**Note:** Start gathering documents early - translations and 
certifications can take time.
""",
        
        CampusFranceStep.HUMAN_LOGIN: """
## Portal Login Required

⚠️ **HUMAN ACTION REQUIRED**

I cannot log into the Campus France portal for you. This is by design:
- Your credentials are private
- Login actions are irreversible
- Security and privacy matter

**What you need to do:**
1. Go to etudes-en-france.fr
2. Log in with your credentials
3. Tell me what you see or what you need help with

I can guide you through the interface once you're logged in.
""",
        
        CampusFranceStep.FORM_REVIEW: """
## Form Review

I can help you review your application:
- Check for completeness
- Verify document uploads
- Review text for errors
- Ensure consistency across materials

**Important:** You should always do a final review yourself before 
submitting.
""",
        
        CampusFranceStep.SUBMISSION: """
## Application Submission

⚠️ **HUMAN ACTION REQUIRED**

I cannot submit your application for you. This is a critical, 
irreversible action that requires your explicit confirmation.

**Before submitting, verify:**
- [ ] All documents are uploaded
- [ ] All forms are complete
- [ ] Payment is processed (if applicable)
- [ ] You've reviewed everything one last time

**When ready:** Log into the portal and submit your application yourself.
I'm here to answer any last-minute questions.
""",
    }
    
    return guidance.get(step, "I can help you with your Campus France application. What specifically do you need assistance with?")


def apply_campus_france_constraints(state: ADEState) -> dict:
    """
    Apply Campus France-specific constraints to the decision.
    
    This function enforces strict safety rules for Campus France tasks:
    - Never store credentials
    - Human must log in
    - Submissions require explicit human action
    
    Args:
        state: Current ADE state
    
    Returns:
        State updates with any necessary overrides
    """
    step = detect_campus_france_step(state["task_input"])
    
    # Steps that absolutely require human action
    human_required_steps = {
        CampusFranceStep.HUMAN_LOGIN,
        CampusFranceStep.SUBMISSION,
    }
    
    # Steps where we can assist but should verify
    assisted_steps = {
        CampusFranceStep.CV_PREPARATION,
        CampusFranceStep.MOTIVATION_LETTER,
        CampusFranceStep.STUDY_PROJECT,
        CampusFranceStep.FORM_REVIEW,
    }
    
    updates = {}
    
    if step in human_required_steps:
        updates["decision"] = DecisionType.HUMAN
        updates["awaiting_human"] = True
    elif step in assisted_steps:
        # These can proceed with tools but should have human review
        updates["decision"] = DecisionType.HUMAN
    
    # Add step guidance to messages
    guidance = get_step_guidance(step)
    
    return updates


def get_campus_france_urls() -> dict[str, str]:
    """
    Get official Campus France URLs.
    
    Returns:
        Dictionary of resource name to URL
    """
    return {
        "main_portal": "https://www.campusfrance.org",
        "etudes_en_france": "https://pastel.diplomatie.gouv.fr/etudesenfrance/",
        "scholarship_search": "https://campusbourses.campusfrance.org",
        "eiffel_program": "https://www.campusfrance.org/en/eiffel-scholarship-program-of-excellence",
        "faq": "https://www.campusfrance.org/en/faq",
    }

