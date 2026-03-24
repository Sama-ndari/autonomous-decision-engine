"""
Browser Tools - Read-only Playwright browser tools.

Provides safe, read-only web browsing capabilities.
No form submissions, no clicks on action buttons, no login.
"""

from typing import Optional
from langchain_core.tools import Tool
from langchain_community.agent_toolkits import PlayWrightBrowserToolkit

# Playwright imports are optional
try:
    from playwright.async_api import async_playwright, Browser, Playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    Browser = None
    Playwright = None

from app.config import get_config


class BrowserTools:
    """
    Safe, read-only browser tools for web content extraction.
    
    Design principles:
    - Read-only by default
    - No form submissions
    - No credential handling
    - No clicking on action buttons
    - Human logs in manually if needed
    """
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.playwright: Optional[Playwright] = None
        self._tools: Optional[list] = None
    
    async def setup(self) -> list:
        """
        Initialize Playwright and return browser tools.
        
        Returns:
            List of LangChain tools for browser interaction
        """
        if not PLAYWRIGHT_AVAILABLE:
            return self._get_fallback_tools()
        
        config = get_config()
        
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=config.browser_headless
        )
        
        # Get standard tools from toolkit
        toolkit = PlayWrightBrowserToolkit.from_browser(
            async_browser=self.browser
        )
        self._tools = toolkit.get_tools()
        
        # Filter to read-only tools and add safety wrappers
        safe_tools = self._wrap_tools_with_safety(self._tools)
        
        return safe_tools
    
    def _wrap_tools_with_safety(self, tools: list) -> list:
        """
        Wrap tools with safety checks.
        
        Filters out dangerous operations and adds logging.
        """
        # Tools that are safe for read-only use
        safe_tool_names = {
            "navigate_browser",
            "current_webpage",
            "extract_text",
            "get_elements",
        }
        
        # Filter and wrap
        safe_tools = []
        for tool in tools:
            if tool.name.lower() in safe_tool_names or "navigate" in tool.name.lower():
                safe_tools.append(tool)
        
        return safe_tools
    
    def _get_fallback_tools(self) -> list:
        """
        Get fallback tools when Playwright is not available.
        
        Returns basic URL fetching capability using requests.
        """
        import requests
        from bs4 import BeautifulSoup
        
        def fetch_page(url: str) -> str:
            """Fetch a webpage and extract its text content."""
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Remove script and style elements
                for element in soup(['script', 'style', 'nav', 'footer']):
                    element.decompose()
                
                text = soup.get_text(separator='\n', strip=True)
                # Limit output size
                return text[:5000] if len(text) > 5000 else text
            except Exception as e:
                return f"Error fetching page: {str(e)}"
        
        return [
            Tool(
                name="fetch_webpage",
                func=fetch_page,
                description="Fetch a webpage and extract its text content. "
                           "Use this for reading public web pages. "
                           "Input should be a valid URL."
            )
        ]
    
    async def cleanup(self):
        """Clean up browser resources."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()


async def get_browser_tools() -> tuple[list, Optional["BrowserTools"]]:
    """
    Get browser tools for the decision engine.
    
    Returns:
        Tuple of (tools list, BrowserTools instance for cleanup)
    """
    browser_tools = BrowserTools()
    tools = await browser_tools.setup()
    return tools, browser_tools

