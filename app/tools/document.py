"""
Document Analysis Tools.

Provides tools for analyzing and extracting information from documents.
Focuses on helping users prepare application materials.
"""

from langchain_core.tools import Tool
from pydantic import BaseModel, Field


class DocumentOutline(BaseModel):
    """Structure for a document outline."""
    
    title: str = Field(description="Document title")
    sections: list[str] = Field(description="Main sections")
    key_points: list[str] = Field(description="Key points to address")
    word_count_target: int = Field(description="Target word count")


class CVGuidance(BaseModel):
    """Guidance for creating a French-format CV."""
    
    sections: list[str] = Field(
        default=[
            "État civil (Personal Information)",
            "Formation (Education)",
            "Expériences professionnelles (Work Experience)",
            "Compétences (Skills)",
            "Langues (Languages)",
            "Centres d'intérêt (Interests)",
        ]
    )
    tips: list[str] = Field(
        default=[
            "Include a professional photo (standard in France)",
            "Put most recent experience first (reverse chronological)",
            "Keep to 1-2 pages maximum",
            "Include date of birth and nationality",
            "Be specific about language levels (use CEFR: A1-C2)",
            "Tailor content to the specific program/position",
        ]
    )


def get_cv_guidance(context: str = "") -> str:
    """
    Get guidance for creating a French-format CV.
    
    Args:
        context: Optional context about the specific application
    
    Returns:
        Detailed guidance string
    """
    guidance = CVGuidance()
    
    result = ["# French CV (Curriculum Vitae) Guidelines\n"]
    
    result.append("## Required Sections:")
    for i, section in enumerate(guidance.sections, 1):
        result.append(f"{i}. {section}")
    
    result.append("\n## Key Tips:")
    for tip in guidance.tips:
        result.append(f"• {tip}")
    
    result.append("\n## Format Notes:")
    result.append("• Use A4 paper format")
    result.append("• Professional, clean layout")
    result.append("• Consistent font (Arial, Calibri, or similar)")
    result.append("• Clear section headers")
    
    if context:
        result.append(f"\n## Specific Context:\n{context}")
    
    return "\n".join(result)


def get_motivation_letter_guidance(context: str = "") -> str:
    """
    Get guidance for writing a French motivation letter.
    
    Args:
        context: Optional context about the specific application
    
    Returns:
        Detailed guidance string
    """
    result = ["# French Motivation Letter (Lettre de Motivation) Guidelines\n"]
    
    result.append("## Structure:")
    result.append("1. **Header**: Your contact info, date, recipient info")
    result.append("2. **Opening**: Why you're writing, which program")
    result.append("3. **Body Paragraph 1**: Your background and qualifications")
    result.append("4. **Body Paragraph 2**: Why this program/school specifically")
    result.append("5. **Body Paragraph 3**: Your project and career goals")
    result.append("6. **Closing**: Polite conclusion, signature")
    
    result.append("\n## Key Elements:")
    result.append("• Personalize for each application")
    result.append("• Show knowledge of the program")
    result.append("• Connect your experience to your goals")
    result.append("• Be specific, avoid generic statements")
    result.append("• Keep to one page")
    
    result.append("\n## French Formalities:")
    result.append('• Start with "Madame, Monsieur," (formal)')
    result.append('• End with a polite formula like:')
    result.append('  "Je vous prie d\'agréer, Madame, Monsieur, '
                  'l\'expression de mes salutations distinguées."')
    
    if context:
        result.append(f"\n## Specific Context:\n{context}")
    
    return "\n".join(result)


def get_study_project_guidance(context: str = "") -> str:
    """
    Get guidance for writing a study project (projet d'études).
    
    Args:
        context: Optional context about the specific application
    
    Returns:
        Detailed guidance string
    """
    result = ["# Study Project (Projet d'Études) Guidelines\n"]
    
    result.append("## Purpose:")
    result.append("The study project explains your academic and professional goals")
    result.append("and how studying in France fits into your plans.\n")
    
    result.append("## Structure:")
    result.append("1. **Introduction**: Brief personal introduction")
    result.append("2. **Academic Background**: Your education so far")
    result.append("3. **Why This Field**: Motivation for your chosen field")
    result.append("4. **Why France**: Specific reasons for studying in France")
    result.append("5. **Program Choice**: Why this specific program/school")
    result.append("6. **Career Goals**: Post-graduation plans")
    result.append("7. **Return Plans**: How you'll use education in home country")
    
    result.append("\n## Key Points:")
    result.append("• Be coherent: past → present → future should connect")
    result.append("• Show research about France and the program")
    result.append("• Be realistic about career goals")
    result.append("• Mention language skills (French learning if applicable)")
    result.append("• Keep between 1-2 pages")
    
    if context:
        result.append(f"\n## Specific Context:\n{context}")
    
    return "\n".join(result)


def get_document_tools() -> list[Tool]:
    """
    Get document analysis and preparation tools.
    
    Returns:
        List of document-related tools
    """
    return [
        Tool(
            name="cv_guidance",
            func=get_cv_guidance,
            description="Get guidance for creating a French-format CV. "
                       "Input can be empty or contain context about the application."
        ),
        Tool(
            name="motivation_letter_guidance",
            func=get_motivation_letter_guidance,
            description="Get guidance for writing a French motivation letter. "
                       "Input can be empty or contain context about the application."
        ),
        Tool(
            name="study_project_guidance",
            func=get_study_project_guidance,
            description="Get guidance for writing a study project (projet d'études). "
                       "Input can be empty or contain context about the application."
        ),
    ]

