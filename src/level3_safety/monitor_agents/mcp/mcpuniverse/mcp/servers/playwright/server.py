"""
Playwright MCP Server - Model Context Protocol integration for Playwright automation

This module provides a FastMCP server that enables Playwright browser automation
through the MCP protocol. It supports browser operations, page interactions, and content extraction.
"""
# pylint: disable=broad-exception-caught
import os
import asyncio
import json
import base64
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

import click
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from mcp.server.fastmcp import FastMCP
from mcpuniverse.common.logger import get_logger


class PlaywrightSession:
    """Represents a browser session"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self.created_at = datetime.now()
        self.is_active = True
    
    async def close(self):
        """Close the browser session"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            print(f"Error closing session: {e}")
        finally:
            self.is_active = False


class PlaywrightManager:
    """Manages Playwright browser sessions"""
    
    def __init__(self):
        self.sessions: Dict[str, PlaywrightSession] = {}
    
    async def get_or_create_session(self) -> PlaywrightSession:
        """Get the latest active session or create a new one"""
        # Find the latest active session
        active_sessions = [s for s in self.sessions.values() if s.is_active]
        if active_sessions:
            return active_sessions[-1]
        
        # Create new session
        session_id = str(uuid.uuid4())
        session = PlaywrightSession(session_id)
        
        # Initialize browser
        session.playwright = await async_playwright().start()
        session.browser = await session.playwright.chromium.launch(headless=True)
        session.context = await session.browser.new_context()
        session.page = await session.context.new_page()
        
        self.sessions[session_id] = session
        return session
    
    async def close_all_sessions(self):
        """Close all active sessions"""
        for session in self.sessions.values():
            if session.is_active:
                await session.close()


def build_server(port: int) -> FastMCP:
    """
    Initializes the Playwright MCP server.

    :param port: Port for SSE.
    :return: The MCP server.
    """
    mcp = FastMCP("playwright", port=port)
    manager = PlaywrightManager()
    
    @mcp.tool()
    async def playwright_navigate(url: str) -> str:
        """
        Navigate to a URL. This will auto create a session if none exists.
        
        Args:
            url: URL to navigate to
            
        Returns:
            Navigation result message
        """
        try:
            session = await manager.get_or_create_session()
            
            # Ensure URL has protocol
            if not url.startswith("http://") and not url.startswith("https://"):
                url = "https://" + url
            
            await session.page.goto(url)
            
            # Get page text content for confirmation
            text_content = await session.page.text_content("body")
            preview = text_content[:200] if text_content else "No content"
            
            return f"Successfully navigated to {url}\nPage content preview:\n{preview}"
            
        except Exception as e:
            return f"Navigation error: {str(e)}"
    
    @mcp.tool()
    async def playwright_screenshot(name: str, selector: Optional[str] = None) -> str:
        """
        Take a screenshot of the current page or a specific element.
        
        Args:
            name: Name for the screenshot
            selector: CSS selector for element to screenshot (null for full page)
            
        Returns:
            Screenshot result with base64 data
        """
        try:
            session = await manager.get_or_create_session()
            
            if selector:
                element = await session.page.locator(selector)
                screenshot_data = await element.screenshot()
            else:
                screenshot_data = await session.page.screenshot(full_page=True)
            
            # Convert to base64
            encoded_string = base64.b64encode(screenshot_data).decode("utf-8")
            
            return json.dumps({
                "name": name,
                "base64": encoded_string,
                "message": f"Screenshot taken: {name}"
            }, indent=2)
            
        except Exception as e:
            return f"Screenshot error: {str(e)}"
    
    @mcp.tool()
    async def playwright_click(selector: str) -> str:
        """
        Click an element on the page using CSS selector.
        
        Args:
            selector: CSS selector for element to click
            
        Returns:
            Click result message
        """
        try:
            session = await manager.get_or_create_session()
            
            # Handle potential new page/tab opening
            async def handle_new_page():
                try:
                    new_page = await session.context.wait_for_event("page", timeout=3000)
                    await new_page.wait_for_load_state()
                    session.page = new_page
                except:
                    pass
            
            # Start waiting for new page before clicking
            new_page_task = asyncio.create_task(handle_new_page())
            
            await session.page.locator(selector).click()
            
            # Wait a bit for potential navigation
            await asyncio.sleep(0.5)
            new_page_task.cancel()
            
            return f"Successfully clicked element with selector: {selector}"
            
        except Exception as e:
            return f"Click error: {str(e)}"
    
    @mcp.tool()
    async def playwright_fill(selector: str, value: str) -> str:
        """
        Fill out an input field.
        
        Args:
            selector: CSS selector for input field
            value: Value to fill
            
        Returns:
            Fill result message
        """
        try:
            session = await manager.get_or_create_session()
            
            await session.page.locator(selector).fill(value)
            return f"Successfully filled element with selector '{selector}' with value: {value}"
            
        except Exception as e:
            return f"Fill error: {str(e)}"
    
    @mcp.tool()
    async def playwright_evaluate(script: str) -> str:
        """
        Execute JavaScript in the browser console.
        
        Args:
            script: JavaScript code to execute
            
        Returns:
            Script execution result
        """
        try:
            session = await manager.get_or_create_session()
            
            result = await session.page.evaluate(script)
            return f"Script executed successfully. Result: {json.dumps(result, default=str)}"
            
        except Exception as e:
            return f"Evaluate error: {str(e)}"
    
    @mcp.tool()
    async def playwright_click_text(text: str) -> str:
        """
        Click an element on the page by its text content.
        
        Args:
            text: Text content of the element to click
            
        Returns:
            Click result message
        """
        try:
            session = await manager.get_or_create_session()
            
            # Handle potential new page/tab opening
            async def handle_new_page():
                try:
                    new_page = await session.context.wait_for_event("page", timeout=3000)
                    await new_page.wait_for_load_state()
                    session.page = new_page
                except:
                    pass
            
            # Start waiting for new page before clicking
            new_page_task = asyncio.create_task(handle_new_page())
            
            await session.page.locator(f"text={text}").nth(0).click()
            
            # Wait a bit for potential navigation
            await asyncio.sleep(0.5)
            new_page_task.cancel()
            
            return f"Successfully clicked element with text: {text}"
            
        except Exception as e:
            return f"Click text error: {str(e)}"
    
    @mcp.tool()
    async def playwright_get_text_content() -> str:
        """
        Get the text content of all visible elements on the page.
        
        Returns:
            Text content of all elements
        """
        try:
            session = await manager.get_or_create_session()
            
            # JavaScript to get unique visible text content
            unique_texts = await session.page.evaluate('''() => {
                var elements = Array.from(document.querySelectorAll('*'));
                var uniqueTexts = new Set();

                for (var element of elements) {
                    if (element.offsetWidth > 0 || element.offsetHeight > 0) {
                        var childrenCount = element.querySelectorAll('*').length;
                        if (childrenCount <= 3) {
                            var innerText = element.innerText ? element.innerText.trim() : '';
                            if (innerText && innerText.length <= 1000) {
                                uniqueTexts.add(innerText);
                            }
                            var value = element.getAttribute('value');
                            if (value) {
                                uniqueTexts.add(value);
                            }
                        }
                    }
                }
                return Array.from(uniqueTexts);
            }''')
            
            return f"Text content of all elements: {unique_texts}"
            
        except Exception as e:
            return f"Get text content error: {str(e)}"
    
    @mcp.tool()
    async def playwright_get_html_content(selector: str) -> str:
        """
        Get the HTML content of a specific element.
        
        Args:
            selector: CSS selector for the element
            
        Returns:
            HTML content of the element
        """
        try:
            session = await manager.get_or_create_session()
            
            html_content = await session.page.locator(selector).inner_html()
            return f"HTML content of element with selector '{selector}': {html_content}"
            
        except Exception as e:
            return f"Get HTML content error: {str(e)}"
    
    @mcp.tool()
    async def playwright_close() -> str:
        """
        Close all browser sessions and release resources.
        
        Returns:
            Close result message
        """
        try:
            await manager.close_all_sessions()
            return "All browser sessions closed successfully"
        except Exception as e:
            return f"Close error: {str(e)}"

    return mcp


@click.command()
@click.option(
    "--transport",
    type=click.Choice(["stdio", "sse"]),
    default="stdio",
    help="Transport type",
)
@click.option("--port", default="8000", help="Port to listen on for SSE")
def main(transport: str, port: str):
    """
    Starts the initialized Playwright MCP server.

    :param port: Port for SSE.
    :param transport: The transport type, e.g., `stdio` or `sse`.
    """
    assert transport.lower() in ["stdio", "sse"], \
        "Transport should be `stdio` or `sse`"
    
    logger = get_logger("Service:playwright")
    logger.info("Starting the Playwright MCP server")
    
    mcp = build_server(int(port))
    mcp.run(transport=transport.lower())


if __name__ == "__main__":
    main()
