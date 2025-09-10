"""
Simple ReAct Agent Implementation with Enhanced Tools
"""

import json
import re
from openai import OpenAI
from config.llm_config import LLMConfig
from tools.enhanced_norm_tools import EnhancedNormTools, get_available_tools_with_prompts


class SimpleReActAgent:
    """Simple ReAct (Reasoning + Acting) agent with tool-specific prompts."""
    
    def __init__(self, config: LLMConfig = None):
        """Initialize the agent."""
        self.config = config or LLMConfig()
        self.client = OpenAI(
            base_url=self.config.local_llm_url,
            api_key=self.config.local_llm_api_key
        )
        self.enhanced_tools = EnhancedNormTools()
        self.max_steps = 5
        
    def get_system_prompt(self) -> str:
        """Create the system prompt with tool descriptions and interpretation guides."""
        tools_json = json.dumps(get_available_tools_with_prompts(), indent=2)
        tool_prompts = self.enhanced_tools.get_tool_prompts()
        
        return f"""You are a ReAct agent for network device management. Follow this pattern:

Thought: Reason about what to do based on user request
Action: 
<tool_call>
{{"name": "tool_name", "arguments": {{"arg1": "value1", "arg2": "value2"}}}}
</tool_call>
Observation: [Will be provided by system with interpretation]

Continue until you have enough information, then:
Final Answer: Your response following the display guidelines

AVAILABLE TOOLS:
{tools_json}

DETAILED TOOL GUIDES:
{tool_prompts}

IMPORTANT RULES:
1. Always start with Thought
2. Execute ONE tool at a time
3. Wait for Observation before continuing
4. Use the interpretation provided in observations
5. Follow the display guidelines for each tool
6. When showing device info, ALWAYS offer detailed report option
7. End with Final Answer when done
8. Keep responses concise but informative
"""
    
    def process_query(self, query: str) -> str:
        """Process a user query through the ReAct loop."""
        return self.run(query)
    
    def run(self, query: str) -> str:
        """Process a user query through the ReAct loop."""
        messages = [
            {"role": "system", "content": self.get_system_prompt()},
            {"role": "user", "content": query}
        ]
        
        for step in range(self.max_steps):
            # Get LLM response
            response = self.client.chat.completions.create(
                model=self.config.local_llm_model,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )
            
            agent_output = response.choices[0].message.content
            print(f"\n--- Step {step + 1} ---")
            print(agent_output)
            
            # Check for final answer
            if "Final Answer:" in agent_output:
                final_match = re.search(r'Final Answer:\s*(.*)', agent_output, re.DOTALL)
                if final_match:
                    return final_match.group(1).strip()
            
            # Parse tool call from agent output
            tool_call = self.parse_tool_call(agent_output)
            if tool_call:
                tool_name = tool_call['name']
                arguments = tool_call.get('arguments', {})
                
                print(f"\nExecuting: {tool_name} with {arguments}")
                
                # Execute tool using enhanced tools
                result = self.enhanced_tools.execute_tool(tool_name, **arguments)
                
                # Format observation with interpretation
                if result["success"]:
                    # Include interpretation directly as the observation
                    interpretation = result.get('interpretation', 'No interpretation available')
                    if tool_name == "get_device_info":
                        observation = f"{interpretation}\n\nIMPORTANT: Now provide your Final Answer with this information. Do NOT call any more tools. Start your response with 'Final Answer:'"
                    else:
                        observation = f"{interpretation}\n\nProvide your Final Answer based on this information."
                else:
                    observation = f"Error - {result.get('error', 'Tool execution failed')}\n\nProvide a Final Answer explaining the issue to the user."
                
                # Add agent response and observation to conversation
                messages.append({"role": "assistant", "content": agent_output})
                messages.append({"role": "user", "content": f"Observation: {observation}"})
            else:
                # No action found, prompt to continue
                messages.append({"role": "assistant", "content": agent_output})
                messages.append({"role": "user", "content": "Continue with your next thought and action, or provide Final Answer."})
        
        return "Max steps reached. Unable to complete the task."
    
    def parse_tool_call(self, response: str):
        """Parse tool call from agent response."""
        patterns = [
            r'<tool_call>\s*(\{.*?\})\s*</tool_call>',
            r'```tool_call\s*(\{.*?\})\s*```'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    continue
        return None


# Example usage
if __name__ == "__main__":
    # Create agent with default config or custom config
    config = LLMConfig()
    agent = SimpleReActAgent(config)
    
    # Test query
    result = agent.run("Show me information about device SRMECH01")
    print(f"\nFinal Result:\n{result}")