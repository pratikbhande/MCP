import json
import asyncio
from typing import Any, Dict, List, Optional
from pydantic import AnyUrl
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPClient:
    """
    MCP Client wrapper class that provides a clean interface to interact with MCP servers.
    Handles resource management, tool execution, resource access, and prompt handling.
    """
    
    def __init__(self, server_script_path: str):
        """
        Initialize the MCP client with the path to the server script.
        
        Args:
            server_script_path: Path to the MCP server Python script
        """
        self.server_script_path = server_script_path
        self.session: Optional[ClientSession] = None
        self._stdio_client = None
    
    async def __aenter__(self):
        """Async context manager entry - establishes connection to MCP server."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleans up connection."""
        await self.cleanup()
    
    async def connect(self):
        """Establish connection to the MCP server."""
        # Set up server parameters for stdio communication
        server_params = StdioServerParameters(
            command="python",
            args=[self.server_script_path]
        )
        
        # Create stdio client connection
        self._stdio_client = stdio_client(server_params)
        
        # Initialize session
        self.session = await self._stdio_client.__aenter__()
        
        # Initialize the session
        await self.session.initialize()
    
    async def cleanup(self):
        """Clean up the connection and session."""
        if self._stdio_client:
            await self._stdio_client.__aexit__(None, None, None)
        self.session = None
        self._stdio_client = None
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        Get list of available tools from the MCP server.
        
        Returns:
            List of tool definitions with names, descriptions, and schemas
        """
        if not self.session:
            raise RuntimeError("Client not connected. Use async context manager or call connect() first.")
        
        result = await self.session.list_tools()
        return result.tools
    
    async def call_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool on the MCP server.
        
        Args:
            tool_name: Name of the tool to execute
            tool_input: Dictionary of arguments for the tool
            
        Returns:
            Tool execution result
        """
        if not self.session:
            raise RuntimeError("Client not connected. Use async context manager or call connect() first.")
        
        result = await self.session.call_tool(tool_name, tool_input)
        return result
    
    async def read_resource(self, uri: str) -> Any:
        """
        Read a resource from the MCP server by URI.
        
        Args:
            uri: Resource URI (e.g., "docs://documents" or "documents/report.pdf")
            
        Returns:
            Resource content - JSON object if application/json, text otherwise
        """
        if not self.session:
            raise RuntimeError("Client not connected. Use async context manager or call connect() first.")
        
        result = await self.session.read_resource(AnyUrl(uri))
        
        # Get the first resource from the contents list
        resource = result.contents[0]
        
        # Parse based on MIME type
        if resource.mime_type == "application/json":
            return json.loads(resource.text)
        else:
            return resource.text
    
    async def list_prompts(self) -> List[Dict[str, Any]]:
        """
        Get list of available prompts from the MCP server.
        
        Returns:
            List of prompt definitions with names and descriptions
        """
        if not self.session:
            raise RuntimeError("Client not connected. Use async context manager or call connect() first.")
        
        result = await self.session.list_prompts()
        return result.prompts
    
    async def get_prompt(self, prompt_name: str, arguments: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Get a prompt from the MCP server with optional arguments.
        
        Args:
            prompt_name: Name of the prompt to retrieve
            arguments: Optional dictionary of arguments to pass to the prompt
            
        Returns:
            List of messages that form the prompt conversation
        """
        if not self.session:
            raise RuntimeError("Client not connected. Use async context manager or call connect() first.")
        
        if arguments is None:
            arguments = {}
        
        result = await self.session.get_prompt(prompt_name, arguments)
        return result.messages


# Example usage and testing
async def test_client():
    """
    Test function to demonstrate MCP client usage.
    Replace 'mcp_server.py' with your actual server script path.
    """
    async with MCPClient("mcp_server.py") as client:
        # Test listing tools
        print("Available tools:")
        tools = await client.list_tools()
        for tool in tools:
            print(f"- {tool['name']}: {tool.get('description', 'No description')}")
        
        # Test calling a tool (example with read_doc_contents)
        try:
            result = await client.call_tool("read_doc_contents", {"doc_id": "report.pdf"})
            print(f"\nDocument contents: {result}")
        except Exception as e:
            print(f"Tool call failed: {e}")
        
        # Test reading resources
        try:
            resource_data = await client.read_resource("docs://documents")
            print(f"\nResource data: {resource_data}")
        except Exception as e:
            print(f"Resource read failed: {e}")
        
        # Test listing prompts
        try:
            prompts = await client.list_prompts()
            print(f"\nAvailable prompts:")
            for prompt in prompts:
                print(f"- {prompt['name']}: {prompt.get('description', 'No description')}")
        except Exception as e:
            print(f"List prompts failed: {e}")


if __name__ == "__main__":
    # Run the test if this file is executed directly
    asyncio.run(test_client())