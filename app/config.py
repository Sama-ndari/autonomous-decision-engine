"""
Configuration module for Autonomous Decision Engine.

Loads environment variables and provides typed configuration access.
"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv(override=True)


@dataclass(frozen=True)
class ModelConfig:
    """LLM model configuration."""
    name: str
    temperature: float


@dataclass(frozen=True)
class RiskThresholds:
    """Risk level thresholds for decision routing.
    
    - Below autonomous: Full autonomy allowed
    - Between autonomous and tools: Tool-assisted with oversight
    - Between tools and human: Requires human confirmation
    - Above human: Refuse to proceed
    """
    autonomous: float  # Max risk for autonomous action
    tools: float       # Max risk for tool-assisted action
    human: float       # Max risk for human-assisted action (above = STOP)


@dataclass(frozen=True)
class Config:
    """Application configuration."""
    
    # API Keys
    openai_api_key: str
    serper_api_key: str | None
    
    # Pushover notifications
    pushover_token: str | None
    pushover_user: str | None
    
    # Model settings
    model: ModelConfig
    
    # Risk thresholds
    risk_thresholds: RiskThresholds
    
    # Database
    checkpoint_db: str
    
    # Browser
    browser_headless: bool
    
    # Logging
    log_level: str


def load_config() -> Config:
    """Load configuration from environment variables."""
    
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")
    
    return Config(
        openai_api_key=openai_key,
        serper_api_key=os.getenv("SERPER_API_KEY"),
        pushover_token=os.getenv("PUSHOVER_TOKEN"),
        pushover_user=os.getenv("PUSHOVER_USER"),
        model=ModelConfig(
            name=os.getenv("ADE_MODEL", "gpt-4o-mini"),
            temperature=float(os.getenv("ADE_TEMPERATURE", "0.1")),
        ),
        risk_thresholds=RiskThresholds(
            autonomous=float(os.getenv("ADE_RISK_THRESHOLD_AUTONOMOUS", "0.3")),
            tools=float(os.getenv("ADE_RISK_THRESHOLD_TOOLS", "0.5")),
            human=float(os.getenv("ADE_RISK_THRESHOLD_HUMAN", "0.7")),
        ),
        checkpoint_db=os.getenv("ADE_CHECKPOINT_DB", "./memory.db"),
        browser_headless=os.getenv("ADE_BROWSER_HEADLESS", "true").lower() == "true",
        log_level=os.getenv("ADE_LOG_LEVEL", "INFO"),
    )


# Global config instance - lazy loaded
_config: Config | None = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = load_config()
    return _config

