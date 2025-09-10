"""
Enhanced Norm Tools with built-in prompts and interpretation
"""

from dataclasses import dataclass
from tools.get_device_info import GetDeviceInfo
from tools.get_device_report import GetDeviceReport


@dataclass
class NormAPIConfig:
    """Configuration for Norm API access."""
    base_url: str = "https://normapi.prd.inet.telenet.be:9123"
    api_key: str = "71b1bf88-9638-11ec-96ab-005056a2b9fd"
    username: str = "mayeid"
    request_id: str = "a2c60f1428d7f083ddc9ed96b2cde79c"


class EnhancedNormTools:
    """Enhanced tools with prompts and interpretation."""
    
    def __init__(self, config: NormAPIConfig = None):
        self.config = config or NormAPIConfig()
        
        # Initialize individual tools
        self.device_info_tool = GetDeviceInfo(self.config)
        self.device_report_tool = GetDeviceReport(self.config)
        
        # Tool registry
        self.tools = {
            "get_device_info": self.device_info_tool,
            "get_device_report": self.device_report_tool
        }
    
    def get_tool_prompts(self):
        """Get all tool prompts for the system prompt."""
        prompts = []
        for name, tool in self.tools.items():
            prompts.append(f"=== TOOL: {name} ===\n{tool.prompt}\n")
        return "\n".join(prompts)
    
    def execute_tool(self, tool_name: str, **kwargs):
        """Execute a tool by name with arguments."""
        if tool_name not in self.tools:
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}",
                "interpretation": f"Tool '{tool_name}' not found. Available tools: {list(self.tools.keys())}"
            }
        
        tool = self.tools[tool_name]
        
        # Execute the tool
        if tool_name == "get_device_info":
            result = tool.execute(kwargs.get("hostname", ""))
        elif tool_name == "get_device_report":
            result = tool.execute(
                kwargs.get("hostname", ""),
                kwargs.get("tags", [])
            )
        
        # Add interpretation to the result
        if result["success"]:
            result["interpretation"] = tool.interpret_response(result)
        
        return result


def get_available_tools_with_prompts():
    """Get tool definitions with their prompts for the agent."""
    return [
        {
            "name": "get_device_info",
            "description": "Get comprehensive device information including interfaces, services, ports, and SAPs",
            "arguments": {
                "hostname": "The device hostname to query (e.g., 'SRMECH01')"
            },
            "usage_guide": """
            Use this tool when:
            - User asks to "show" or "get info" about a device
            - User provides just a device name
            - You need to discover what components a device has
            
            CRITICAL: After using this tool:
            - Provide Final Answer immediately with the interpretation
            - Do NOT automatically call get_device_report
            - End your Final Answer with: "Would you like a detailed report for this device?"
            """
        },
        {
            "name": "get_device_report",
            "description": "Get detailed device report with system info, interfaces, services, and alarms",
            "arguments": {
                "hostname": "The device hostname",
                "tags": "List of device tags - use ['TIMOS', 'CORE'] for TIMOS devices or ['CE', 'COMWARE'] for COMWARE devices"
            },
            "usage_guide": """
            Use this tool when:
            - User wants a "detailed report" or "full details"
            - User says "yes" after you offered a detailed report
            - User asks about system info, uptime, or alarms
            
            IMPORTANT: You must know the device type first!
            - For TIMOS routers: use tags=['TIMOS', 'CORE']
            - For COMWARE switches: use tags=['CE', 'COMWARE']
            
            If you get a 409 error, try the other tag combination.
            """
        }
    ]