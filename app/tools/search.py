"""
Web Search Tools.

Provides web search capabilities using available search APIs.
Prioritizes Serper (Google Search API) with fallback to DuckDuckGo.
"""

import os
from langchain_core.tools import Tool

from app.config import get_config


def create_search_tool() -> Tool:
    """
    Create a web search tool.
    
    Uses Serper API if available, otherwise provides a fallback.
    
    Returns:
        LangChain Tool for web search
    """
    config = get_config()
    
    if config.serper_api_key:
        return _create_serper_tool(config.serper_api_key)
    else:
        return _create_fallback_search_tool()


def _create_serper_tool(api_key: str) -> Tool:
    """Create a search tool using Serper (Google Search API)."""
    from langchain_community.utilities import GoogleSerperAPIWrapper
    
    # Set the API key in environment for the wrapper
    os.environ["SERPER_API_KEY"] = api_key
    
    serper = GoogleSerperAPIWrapper()
    
    return Tool(
        name="web_search",
        func=serper.run,
        description="Search the web for current information. "
                   "Use this when you need to find up-to-date information, "
                   "verify facts, or research a topic. "
                   "Input should be a search query string."
    )


def _create_fallback_search_tool() -> Tool:
    """Create a fallback search tool when no API is available."""
    
    def fallback_search(query: str) -> str:
        """Fallback search that explains the limitation."""
        return (
            f"Web search for '{query}' is not available. "
            "No search API key (SERPER_API_KEY) is configured. "
            "To enable web search, add your Serper API key to the .env file. "
            "For now, I'll work with the information I have available."
        )
    
    return Tool(
        name="web_search",
        func=fallback_search,
        description="Search the web for information. "
                   "Note: This tool requires API configuration to work. "
                   "Input should be a search query string."
    )


def get_search_tools() -> list[Tool]:
    """
    Get all search-related tools.
    
    Returns:
        List of search tools
    """
    return [create_search_tool()]

