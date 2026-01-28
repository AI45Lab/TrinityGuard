"""
An MCP server for Google search with Serper API (primary) and SerpAPI (fallback)
"""
# pylint: disable=broad-exception-caught
import os
import json
import math
from typing import List, Dict, Any

import httpx
import click
from mcp.server.fastmcp import FastMCP
from mcpuniverse.common.logger import get_logger

SERPER_API_BASE = "https://google.serper.dev/search"
SERP_API_BASE = "https://serpapi.com/search.json"
SERPER_API_KEY = os.environ.get("SERPER_API_KEY", "")
SERP_API_KEY = os.environ.get("SERP_API_KEY", "")


async def _search_serper(
        query: str,
        location: str = "",
        num_items: int = 20,
        timeout: float = 60
) -> List[Dict[str, Any]]:
    """
    Make a request to the Serper API.

    :param query: The search query string.
    :param location: The location for the search query.
    :param num_items: The maximum number of results to return.
    :param timeout: The timeout.
    """
    all_items = []
    num_pages = int(math.ceil(num_items / 10))
    num_items_per_page = 10

    for page in range(num_pages):
        offset = page * num_items_per_page
        payload = {
            "q": query,
            "num": num_items_per_page,
            "start": offset
        }
        
        if location:
            payload["gl"] = location  # Google location parameter
        
        headers = {
            "X-API-KEY": SERPER_API_KEY,
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                SERPER_API_BASE, 
                json=payload, 
                headers=headers, 
                timeout=timeout
            )
            response.raise_for_status()
            results = response.json()
            all_items.extend([{
                "position": result.get("position", 0) + offset,
                "title": result.get("title", ""),
                "snippet": result.get("snippet", ""),
                "link": result.get("link", ""),
            } for result in results.get("organic", [])])
    return all_items[:num_items]


async def _search_serpapi(
        query: str,
        location: str = "",
        engine: str = "google",
        num_items: int = 20,
        timeout: float = 60
) -> List[Dict[str, Any]]:
    """
    Make a request to the Serp API.

    :param query: The search query string.
    :param location: The location for the search query.
    :param engine: The search engine to use (default is "google").
    :param num_items: The maximum number of results to return.
    :param timeout: The timeout.
    """
    all_items = []
    num_pages = int(math.ceil(num_items / 10))
    num_items_per_page = 10

    for page in range(num_pages):
        offset = page * num_items_per_page
        params = {
            "api_key": SERP_API_KEY,
            "q": query,
            "location": location,
            "engine": engine,
            "num": num_items_per_page,
            "start": offset
        }
        async with httpx.AsyncClient() as client:
            response = await client.get(SERP_API_BASE, params=params, timeout=timeout)
            response.raise_for_status()
            results = response.json()
            all_items.extend([{
                "position": result.get("position", 0) + offset,
                "title": result.get("title", ""),
                "snippet": result.get("snippet", ""),
                "link": result.get("link", ""),
            } for result in results.get("organic_results", [])])
    return all_items[:num_items]


async def _search(
        query: str,
        location: str = "",
        num_items: int = 20,
        timeout: float = 30
) -> List[Dict[str, Any]]:
    """
    Search with Serper API (primary) and fallback to SerpAPI.

    :param query: The search query string.
    :param location: The location for the search query.
    :param num_items: The maximum number of results to return.
    :param timeout: The timeout.
    """
    # Try Serper API first if key is available
    if SERPER_API_KEY:
        try:
            return await _search_serper(query, location, num_items, timeout)
        except Exception as e:
            logger = get_logger("Service:google_search")
            logger.warning(f"Serper API failed, trying SerpAPI: {str(e)}")
    
    # Fallback to SerpAPI if Serper fails or no key
    if SERP_API_KEY:
        try:
            return await _search_serpapi(query, location, num_items, timeout)
        except Exception as e:
            logger = get_logger("Service:google_search")
            logger.error(f"SerpAPI also failed: {str(e)}")
            raise e
    else:
        raise Exception("No API keys available. Please set either SERPER_API_KEY or SERP_API_KEY environment variable.")


def build_server(port: int) -> FastMCP:
    """
    Initializes the MCP server.

    :param port: Port for SSE.
    :return: The MCP server.
    """
    mcp = FastMCP("google_search", port=port)

    @mcp.tool()
    async def search(query: str, location: str = "", num_items: int = 20) -> str:
        """
        A tool to execute the Google search using Serper API (primary) and SerpAPI (fallback).

        Args:
            query: The search query string.
            location: The location for the search query (optional).
            num_items: The maximum number of results to return (default: 20).
        """
        items = []
        try:
            items = await _search(query=query, location=location, num_items=num_items)
            return "\n".join([json.dumps(item, ensure_ascii=False, indent=2) for item in items])
        except Exception as e:
            return json.dumps({"error": f"Search failed: {str(e)}"})

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
    print(f"Starting the MCP server on port {port} with transport {transport}")
    assert transport.lower() in ["stdio", "sse"], \
        "Transport should be `stdio` or `sse`"
    logger = get_logger("Service:google_search")
    logger.info("Starting the MCP server")
    mcp = build_server(int(port))
    mcp.run(transport=transport.lower())
