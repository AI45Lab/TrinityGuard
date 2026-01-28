"""
URL Fetch MCP Server - Model Context Protocol integration for URL content fetching

This module provides a FastMCP server that enables fetching content from URLs
through the MCP protocol. It supports fetching text and JSON content with proper error handling.
"""
# pylint: disable=broad-exception-caught
import base64
import json
import logging
from typing import Annotated, Dict, Optional, Union, Any

import click
import httpx
from pydantic import AnyUrl, Field
from mcp.server.fastmcp import FastMCP, Context
from mcpuniverse.common.logger import get_logger


def build_server(port: int) -> FastMCP:
    """
    Initializes the MCP server.

    :param port: Port for SSE.
    :return: The MCP server.
    """
    mcp = FastMCP("url_fetch", port=port)

    @mcp.tool()
    async def fetch_url(
        url: Annotated[AnyUrl, Field(description="The URL to fetch")],
        headers: Annotated[
            Optional[Dict[str, str]], Field(description="Additional headers to send with the request")
        ] = None,
        timeout: Annotated[int, Field(description="Request timeout in seconds")] = 10,
        ctx: Context = None,
    ) -> str:
        """Fetch content from a URL and return it as text.
        
        This tool allows Claude to retrieve content from any accessible web URL.
        The content is returned as text, making it suitable for HTML, plain text,
        and other text-based content types.
        """
        if ctx:
            await ctx.info(f"Fetching content from URL: {url}")
        
        request_headers = {
            "User-Agent": "URL-Fetch-MCP/0.1.0",
        }
        
        if headers:
            request_headers.update(headers)
        
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
            try:
                response = await client.get(str(url), headers=request_headers)
                response.raise_for_status()
                
                content_type = response.headers.get("content-type", "text/plain")
                
                if ctx:
                    await ctx.info(f"Successfully fetched content ({len(response.text)} bytes, type: {content_type})")
                
                return response.text
            
            except Exception as e:
                error_message = f"Error fetching URL {url}: {str(e)}"
                if ctx:
                    await ctx.error(error_message)
                return error_message

    @mcp.tool()
    async def fetch_json(
        url: Annotated[AnyUrl, Field(description="The URL to fetch JSON from")],
        headers: Annotated[
            Optional[Dict[str, str]], Field(description="Additional headers to send with the request")
        ] = None,
        timeout: Annotated[int, Field(description="Request timeout in seconds")] = 10,
        ctx: Context = None,
    ) -> str:
        """Fetch JSON from a URL, parse it, and return it formatted.
        
        This tool allows Claude to retrieve and parse JSON data from any accessible web URL.
        The JSON is prettified for better readability.
        """
        if ctx:
            await ctx.info(f"Fetching JSON from URL: {url}")
        
        request_headers = {
            "User-Agent": "URL-Fetch-MCP/0.1.0",
            "Accept": "application/json",
        }
        
        if headers:
            request_headers.update(headers)
        
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
            try:
                response = await client.get(str(url), headers=request_headers)
                response.raise_for_status()
                
                content_type = response.headers.get("content-type", "")
                
                if "json" not in content_type and not content_type.startswith("application/json"):
                    # Try to parse anyway, but warn
                    if ctx:
                        await ctx.warning(f"URL did not return JSON content-type (got: {content_type})")
                
                # Parse and format JSON
                try:
                    json_data = response.json()
                    formatted_json = json.dumps(json_data, indent=2)
                    
                    if ctx:
                        await ctx.info(f"Successfully fetched and parsed JSON ({len(formatted_json)} bytes)")
                    
                    return formatted_json
                
                except json.JSONDecodeError as e:
                    error_message = f"Failed to parse JSON from response: {str(e)}"
                    if ctx:
                        await ctx.error(error_message)
                    return error_message
            
            except Exception as e:
                error_message = f"Error fetching JSON from URL {url}: {str(e)}"
                if ctx:
                    await ctx.error(error_message)
                return error_message

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
    Starts the initialized MCP server.

    :param port: Port for SSE.
    :param transport: The transport type, e.g., `stdio` or `sse`.
    """
    assert transport.lower() in ["stdio", "sse"], \
        "Transport should be `stdio` or `sse`"
    
    logger = get_logger("Service:url_fetch")
    logger.info("Starting the URL Fetch MCP server")
    
    mcp = build_server(int(port))
    
    # Only pass port for SSE transport
    if transport == "sse":
        mcp.run(transport=transport, port=int(port))
    else:
        mcp.run(transport=transport)


if __name__ == "__main__":
    main()