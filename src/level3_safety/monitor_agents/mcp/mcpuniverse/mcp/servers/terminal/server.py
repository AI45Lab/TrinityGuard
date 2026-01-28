"""
Terminal MCP Server - Model Context Protocol integration for terminal commands

This module provides a FastMCP server that enables remote execution of terminal commands
through the MCP protocol. It supports running shell commands in a controlled workspace environment.
"""
import os
import subprocess
import click
from typing import Dict, Any
from dotenv import load_dotenv

from mcp.server.fastmcp import FastMCP
from mcpuniverse.common.logger import get_logger

# Load environment variables from .env file
load_dotenv()


def build_server(port: int) -> FastMCP:
    """
    Initializes the MCP server.

    :param port: Port for SSE.
    :return: The MCP server.
    """
    mcp = FastMCP("terminal", port=port)
    
    # Get working directory from environment variable, fallback to default
    default_working_directory =  os.environ.get("TERMINAL_WORKING_DIRECTORY", os.path.expanduser("~/mcp/workspace"))
    
    @mcp.tool()
    async def run_command(command: str) -> str:
        """
        Run a terminal command inside the workspace directory.
        
        Args:
            command: The shell command to run.
            
        Returns:
            The command output or an error message.
        """
        try:
            result = subprocess.run(
                command, 
                shell=True, 
                capture_output=True, 
                cwd=default_working_directory, 
                text=True
            )
            
            output = result.stdout if result.stdout else ""
            error = result.stderr if result.stderr else ""
            
            # Combine output and error, but prioritize output
            if output:
                return output + (f"\n\nErrors:\n{error}" if error else "")
            elif error:
                return f"Command completed with errors:\n{error}"
            else:
                return "Command completed successfully with no output."
                
        except Exception as e:
            return f"Error executing command: {str(e)}"

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
    
    logger = get_logger("Service:terminal")
    logger.info("Starting the Terminal MCP server")
    
    mcp = build_server(int(port))
    mcp.run(transport=transport.lower())


if __name__ == "__main__":
    main()
    