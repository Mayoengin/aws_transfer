"""
Tool management utilities for ReAct Agent
"""

import json
import re
import logging
from typing import Dict, Any, Optional
from tools.norm_tools import NormTools

logger = logging.getLogger(__name__)


class ToolManager:
    """Handles tool parsing and execution for the ReAct agent."""
    
    def __init__(self, norm_tools: NormTools):
        self.norm_tools = norm_tools
    
    def parse_tool_call(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse tool call from agent response."""
        # Check for both XML format and markdown code block format
        patterns = [
            r'<tool_call>\s*(\{.*?\})\s*</tool_call>',  # XML format
            r'```tool_call\s*(\{.*?\})\s*```'  # Markdown code block format
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.DOTALL)
            if match:
                try:
                    tool_call = json.loads(match.group(1))
                    # Validate tool call structure
                    if "name" in tool_call:
                        return tool_call
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse tool call JSON: {e}")
                    logger.debug(f"Failed JSON string: {match.group(1)}")
        
        return None
    
    def execute_tool(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool and return the result."""
        tool_name = tool_call.get("name")
        arguments = tool_call.get("arguments", {})
        
        try:
            if tool_name == "get_device_info":
                result = self.norm_tools.get_device_info(**arguments)
            elif tool_name == "get_device_report":
                result = self.norm_tools.get_device_report(**arguments)
            else:
                return {
                    "success": False,
                    "error": f"Unknown tool '{tool_name}'"
                }
            
            return result
                
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return {
                "success": False,
                "error": f"Error executing tool: {str(e)}"
            }
    
    def find_all_tool_calls(self, response: str) -> list:
        """Find all tool calls in a response."""
        tool_calls_found = []
        patterns = [
            r'<tool_call>\s*(\{.*?\})\s*</tool_call>',  # XML format
            r'```tool_call\s*(\{.*?\})\s*```'  # Markdown code block format
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, response, re.DOTALL):
                try:
                    tool_call = json.loads(match.group(1))
                    if "name" in tool_call:
                        tool_calls_found.append(tool_call)
                except json.JSONDecodeError:
                    continue
        
        return tool_calls_found
    
    def generate_tool_id(self, tool_call: Dict[str, Any]) -> str:
        """Generate a unique ID for a tool call to track execution."""
        import hashlib
        # Create unique ID based on tool name + arguments to prevent duplicate executions
        tool_str = f"{tool_call.get('name')}_{str(tool_call.get('arguments', {}))}"
        return hashlib.md5(tool_str.encode()).hexdigest()[:8]