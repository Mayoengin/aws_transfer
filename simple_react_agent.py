"""
Simple ReAct Agent Implementation with Enhanced Tools - AWS Bedrock version
"""

import json
import re
import boto3
from botocore.exceptions import ClientError
from config.llm_config import LLMConfig
from tools.enhanced_norm_tools import EnhancedNormTools, get_available_tools_with_prompts


class SimpleReActAgent:
    """Simple ReAct (Reasoning + Acting) agent with tool-specific prompts using AWS Bedrock."""
    
    def __init__(self, config: LLMConfig = None):
        """Initialize the agent."""
        self.config = config or LLMConfig()
        
        # Initialize AWS Bedrock client
        self.bedrock_client = boto3.client(
            'bedrock-runtime',
            region_name=self.config.aws_region
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
    
    def call_bedrock(self, messages: list) -> str:
        """Call AWS Bedrock Claude model."""
        try:
            # Convert messages to Claude format
            system_message = ""
            conversation = []
            
            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    conversation.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
            
            # Prepare the request body
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
                "messages": conversation
            }
            
            # Add system message if present
            if system_message:
                request_body["system"] = system_message
            
            # Call Bedrock
            response = self.bedrock_client.invoke_model(
                modelId=self.config.model_id,
                body=json.dumps(request_body),
                contentType='application/json'
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            return response_body['content'][0]['text']
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'AccessDeniedException':
                raise Exception(f"Access denied to model {self.config.model_id}. Please check your AWS permissions and model access in Bedrock console.")
            elif error_code == 'ValidationException':
                raise Exception(f"Invalid request to Bedrock: {e.response['Error']['Message']}")
            else:
                raise Exception(f"Bedrock error ({error_code}): {e.response['Error']['Message']}")
        except Exception as e:
            raise Exception(f"Error calling Bedrock: {str(e)}")
    
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
            # Get LLM response using Bedrock
            try:
                agent_output = self.call_bedrock(messages)
                print(f"\n--- Step {step + 1} ---")
                print(agent_output)
            except Exception as e:
                return f"Error communicating with AWS Bedrock: {str(e)}\n\nPlease check:\n1. AWS credentials are configured (run 'aws configure')\n2. You have access to Claude 3.7 Sonnet in eu-central-1 region\n3. Your AWS permissions include Bedrock access"
            
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
    # Create agent with default config
    config = LLMConfig()
    agent = SimpleReActAgent(config)
    
    # Test query
    result = agent.run("Show me information about device SRMECH01")
    print(f"\nFinal Result:\n{result}")