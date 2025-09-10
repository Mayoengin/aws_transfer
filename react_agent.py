"""
ReAct Agent for Norm Data Manipulation
"""

import json
import re
import logging
from typing import Dict, Any, List, Optional
from openai import OpenAI
from config.llm_config import llm_config
from tools.norm_tools import NormTools, get_available_tools
from utils.formatters import ResponseFormatter
from utils.tool_manager import ToolManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ReActAgent:
    """ReAct (Reasoning + Acting) agent for network device management."""
    
    def __init__(self, config=None):
        """Initialize the ReAct agent."""
        self.llm_config = config or llm_config
        self.client = OpenAI(
            base_url=self.llm_config.local_llm_url,
            api_key=self.llm_config.local_llm_api_key
        )
        self.norm_tools = NormTools()
        self.max_iterations = 5
        self.conversation_history = []
        self.last_device_info = None  # Track last device info for follow-up queries
        
        # Initialize utility classes
        self.formatter = ResponseFormatter()
        self.tool_manager = ToolManager(self.norm_tools)
        
    def _get_system_prompt(self) -> str:
        """Generate the system prompt with available tools."""
        tools_description = json.dumps(get_available_tools(), indent=2)
        
        system_prompt = f"""You are a NORM Services AI assistant following the ReAct (Reasoning + Acting) pattern for network device discovery and monitoring.

You help users query and manage network devices including TIMOS (Nokia/Alcatel-Lucent) routers and ATOSNT (Atos Network Terminal) devices.

CONVERSATION CONTEXT:
- You have access to previous messages in the conversation history
- When a user says "yes" after you've offered a detailed report, look at the conversation history to find the device hostname and tags from the previous device info query
- Extract the device information from the most recent get_device_info result in this conversation
- CRITICAL: Always check conversation history for context about which device was queried

CRITICAL: You MUST follow the ReAct pattern exactly:

1. **Thought**: Always start by reasoning about what you need to do
2. **Action**: Take actions using available tools  
3. **Observation**: You will receive observations from your actions
4. **Final Answer**: Provide your complete response to the user

Available tools:
{tools_description}

**RESPONSE FORMAT - FOLLOW EXACTLY:**

For each step, respond ONLY with:

Thought: [Your reasoning about what needs to be done and why]

Action: 
<tool_call>
{{"name": "<tool-name>", "arguments": {{"arg1": "value1"}}, "id": 1}}
</tool_call>

Then STOP and WAIT for the Observation. DO NOT write mock observations or continue the chain yourself.

After you receive a real Observation from the system, you can either:
1. Continue with another Thought/Action if more information is needed
2. Provide a Final Answer if you have sufficient information

Final Answer: [Your complete response to the user in natural language]

**FOLLOW-UP BEHAVIOR:**
- After using get_device_info tool:
  - IMMEDIATELY provide a Final Answer with the basic device information
  - DO NOT call any other tools
  - DO NOT automatically call get_device_report
  - End your Final Answer with: "Would you like me to show you the detailed report of this device?"
  - WAIT for user response before any further actions
- When user responds with YES/SURE/OK to your question:
  - Look at the conversation history to identify the device hostname and tags from the most recent get_device_info call
  - CRITICAL: Extract the EXACT hostname and tags from the device info observation in the conversation history
  - For SRMECH01, use tags: ["TIMOS", "CORE", "RESIDENTIAL", "BSOD", "SR", "HE_MECH", "SO_HOBO", "MIXED_CLI"]  
  - For CEAWPDGA05, use tags: ["VPRN", "CPE", "COMWARE", "CE"]
  - CRITICAL: Use the hostname and tags from the SAME conversation context
  - In your Final Answer, present ONLY the detailed report data
  - DO NOT ask "Would you like me to show you the detailed report?" again - you're already showing it!
- NEVER automatically fetch the detailed report without user confirmation
- ONE TOOL EXECUTION PER USER REQUEST UNLESS EXPLICITLY ASKED FOR MORE

IMPORTANT RULES:
- NEVER write "Observation:" yourself - wait for the system to provide it
- NEVER include example data or mock responses
- Execute ONE tool at a time and wait for its real result
- Always start with a Thought
- Use tools when you need to fetch device data
- Provide clear, human-readable Final Answers
- If a tool call fails, explain the error and suggest alternatives
- After get_device_info, offer to show detailed report ONCE
- After get_device_report, just present the data - NO follow-up questions
- Do NOT add closing statements like "No further action needed" or "Is there anything else?"
- Present the data clearly and let the user decide what to do next
- CRITICAL: NEVER call the same tool with the same arguments multiple times
- If you get an observation, use it immediately - don't call the tool again
- If you find yourself repeating the same action, STOP and provide a Final Answer
- Each tool should only be called ONCE per conversation unless specifically requested again

TOOL USAGE GUIDE:
- get_device_info: Use when user asks to "show" or "get info" about a device → Ask if they want detailed report
- get_device_report: Use when user says "yes" to detailed report
  * CRITICAL: Look at conversation history to find the device that was just queried
  * Extract hostname and tags from the most recent get_device_info observation in the conversation
  * EXAMPLES of tag patterns:
    - SRMECH01: use hostname="SRMECH01", tags=["TIMOS", "CORE", "RESIDENTIAL", "BSOD", "SR", "HE_MECH", "SO_HOBO", "MIXED_CLI"]
    - CEAWPDGA05: use hostname="CEAWPDGA05", tags=["VPRN", "CPE", "COMWARE", "CE"]
  * DO NOT hardcode device names - extract them from conversation history
  * After showing report: Just present data, NO more questions!
- Flow: get_device_info → "Want detailed report?" → YES → get_device_report (with hostname+tags from history!) → STOP"""
        
        return system_prompt
    
    def _parse_tool_call(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse tool call from agent response."""
        return self.tool_manager.parse_tool_call(response)
    
    def _execute_tool(self, tool_call: Dict[str, Any]) -> str:
        """Execute a tool and return the observation."""
        result = self.tool_manager.execute_tool(tool_call)
        
        if result["success"]:
            return self.formatter.format_observation(result)
        else:
            return f"Tool execution failed: {result.get('error', 'Unknown error')}"
    
    def _format_observation(self, result: Dict[str, Any]) -> str:
        """Format tool result into a human-readable observation."""
        return self.formatter.format_observation(result)
    
    
    
    def process_query(self, user_query: str) -> str:
        """Process a user query using ReAct pattern."""
        self.conversation_history.append({"role": "user", "content": user_query})
        
        # Build messages from conversation history for context
        messages = [{"role": "system", "content": self._get_system_prompt()}]
        
        # Add recent conversation history for context (last 5 exchanges)
        recent_history = self.conversation_history[-10:] if len(self.conversation_history) > 10 else self.conversation_history
        for entry in recent_history:
            messages.append({"role": entry["role"], "content": entry["content"]})
        
        # Check if this is a "yes" response to a detailed report request
        if user_query.lower().strip() in ['yes', 'y', 'sure', 'ok', 'okay', 'yep', 'yeah']:
            # Look for the most recent assistant message that asked about detailed report
            for i in reversed(range(len(self.conversation_history))):
                entry = self.conversation_history[i]
                if (entry.get("role") == "assistant" and 
                    "detailed report" in entry.get("content", "").lower() and
                    "?" in entry.get("content", "")):
                    # This is a response to detailed report question
                    if self.last_device_info:
                        hostname = self.last_device_info.get('hostname', 'UNKNOWN')
                        messages.append({"role": "user", "content": f"{user_query} - User confirmed they want the detailed report for {hostname}. Extract the device tags from the conversation history and call get_device_report with hostname='{hostname}' and the appropriate tags."})
                    else:
                        messages.append({"role": "user", "content": f"{user_query} - User confirmed they want the detailed report. Look at the conversation history to find the device hostname and tags from the most recent device info query, then call get_device_report with those exact details."})
                    break
        
        current_context = ""
        iterations = 0
        tool_executions = []  # Track executed tools
        last_response = ""  # Track last response to detect loops
        identical_response_count = 0
        device_info_executed = False  # Track if get_device_info was executed
        device_report_executed = False  # Track if get_device_report was executed
        
        while iterations < self.max_iterations:
            iterations += 1
            
            try:
                # Log current conversation state
                logger.info(f"Messages sent to LLM (iteration {iterations}): {len(messages)} messages")
                if logger.isEnabledFor(logging.DEBUG):
                    for i, msg in enumerate(messages):
                        logger.debug(f"Message {i}: {msg['role']} - {msg['content'][:100]}...")
                
                # Get LLM response
                response = self.client.chat.completions.create(
                    model=self.llm_config.local_llm_model,
                    messages=messages,
                    temperature=self.llm_config.temperature,
                    max_tokens=self.llm_config.max_tokens
                )
                
                agent_response = response.choices[0].message.content
                logger.info(f"LLM Response (iteration {iterations}):\n{agent_response[:200]}...")
                logger.debug(f"Full LLM Response (iteration {iterations}):\n{agent_response}")
                
                # Detect if we're getting identical responses (stuck in a loop)
                if agent_response.strip() == last_response.strip():
                    identical_response_count += 1
                    if identical_response_count >= 2:
                        logger.warning(f"Detected loop - identical response {identical_response_count} times")
                        # Force a final answer extraction or break the loop
                        if any(tool_id in tool_executions for tool_call in self.tool_manager.find_all_tool_calls(agent_response) 
                               for tool_id in [self.tool_manager.generate_tool_id(tool_call)]):
                            # We've already executed the tool, force final answer
                            messages.append({"role": "user", "content": "You already executed this tool. Please provide your Final Answer based on the observation you received."})
                        else:
                            # No tools executed but stuck in loop, extract what we can
                            loop_msg = f"The agent got stuck in a reasoning loop. Here's the context gathered:\n{current_context}"
                            self.conversation_history.append({"role": "assistant", "content": loop_msg})
                            return loop_msg
                else:
                    identical_response_count = 0
                
                last_response = agent_response
                current_context += agent_response + "\n"
                
                # Parse all tool calls in the response (there might be multiple)
                tool_calls_found = self.tool_manager.find_all_tool_calls(agent_response)
                logger.info(f"Found {len(tool_calls_found)} tool calls in response")
                
                # Execute the first unexecuted tool call
                tool_executed = False
                for tool_call in tool_calls_found:
                    tool_id = self.tool_manager.generate_tool_id(tool_call)
                    
                    # Skip if already executed or if get_device_info was already called and this is a repeat
                    if tool_id in tool_executions:
                        continue
                    if device_info_executed and tool_call['name'] == 'get_device_info':
                        logger.info("Skipping duplicate get_device_info call")
                        continue
                    if device_report_executed:
                        logger.info("Device report already executed - no more tools allowed")
                        continue
                        
                    # Execute this tool
                    observation = self._execute_tool(tool_call)
                    observation_text = f"Observation: {observation}"
                    current_context += f"\n{observation_text}\n"
                    
                    # Mark as executed
                    tool_executions.append(tool_id)
                    if tool_call['name'] == 'get_device_info':
                        device_info_executed = True
                        # Store the device info for potential follow-up queries
                        self.last_device_info = {
                            'hostname': tool_call.get('arguments', {}).get('hostname'),
                            'observation': observation_text
                        }
                    elif tool_call['name'] == 'get_device_report':
                        device_report_executed = True
                    
                    # Add the tool call and observation to conversation
                    messages.append({"role": "assistant", "content": agent_response})
                    
                    # Force Final Answer after tool execution
                    if tool_call['name'] == 'get_device_info':
                        messages.append({"role": "user", "content": f"{observation_text}\n\nBased on this observation, provide your Final Answer with the device information and ask if the user wants a detailed report. Do NOT call any more tools. Start your response with 'Final Answer:'"})
                    elif tool_call['name'] == 'get_device_report':
                        messages.append({"role": "user", "content": f"{observation_text}\n\nYou have successfully retrieved the detailed report. Now provide your Final Answer summarizing the key information from this report in a user-friendly format. Do NOT call any additional tools. Do NOT ask any more questions. STOP after providing the Final Answer. Start your response with 'Final Answer:'"})
                    else:
                        messages.append({"role": "user", "content": observation_text})
                    
                    logger.info(f"Tool executed: {tool_call['name']}")
                    tool_executed = True
                    break  # Process one tool at a time
                
                if not tool_executed:
                    # Check if all tools in the response have already been executed
                    all_tools_executed = tool_calls_found and all(
                        self.tool_manager.generate_tool_id(tool_call) in tool_executions 
                        for tool_call in tool_calls_found
                    )
                    
                    if all_tools_executed:
                        # All tools were already executed, prompt for final answer
                        if device_report_executed:
                            messages.append({"role": "user", "content": "You already executed get_device_report. Please provide your Final Answer with the detailed report information. Do NOT call any more tools. Start with 'Final Answer:'"})
                        elif device_info_executed:
                            messages.append({"role": "user", "content": "You already executed get_device_info. Please provide your Final Answer with the device information and ask if the user wants a detailed report. Start with 'Final Answer:'"})
                        else:
                            messages.append({"role": "user", "content": "All tools have been executed. Please provide your Final Answer based on the observations received."})
                        continue
                    
                    # No new tools to execute, check for final answer
                    if "Final Answer:" in agent_response:
                        final_answer_match = re.search(r'Final Answer:\s*(.*)', agent_response, re.DOTALL)
                        if final_answer_match:
                            final_answer = final_answer_match.group(1).strip()
                            self.conversation_history.append({
                                "role": "assistant", 
                                "content": final_answer
                            })
                            return final_answer
                    
                    # If response contains mock observations, extract the actual action needed
                    if "Observation:" in agent_response and "<tool_call>" in agent_response:
                        # LLM might have provided mock observations, prompt to execute actual tools
                        messages.append({"role": "assistant", "content": agent_response})
                        messages.append({"role": "user", "content": "I see you've planned the actions. Now execute the first tool call to get real observations."})
                    else:
                        # No tools and no final answer, prompt for next action or final answer
                        messages.append({"role": "assistant", "content": agent_response})
                        if device_report_executed:
                            messages.append({"role": "user", "content": "You already have the detailed report. Please provide your Final Answer summarizing the report information. Do NOT call any more tools. Start with 'Final Answer:'"})
                        elif device_info_executed:
                            messages.append({"role": "user", "content": "You already have the device information. Please provide your Final Answer and ask if the user wants a detailed report. Start with 'Final Answer:'"})
                        else:
                            messages.append({"role": "user", "content": "Please continue with the next action or provide your Final Answer based on the information gathered."})
                    
            except Exception as e:
                logger.error(f"Error in ReAct loop: {e}")
                error_msg = f"I encountered an error while processing your request: {str(e)}"
                self.conversation_history.append({"role": "assistant", "content": error_msg})
                return error_msg
        
        # Max iterations reached
        timeout_msg = "I've reached the maximum number of reasoning steps. Based on what I've gathered so far, here's what I found:\n" + current_context
        self.conversation_history.append({"role": "assistant", "content": timeout_msg})
        return timeout_msg
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get the conversation history."""
        return self.conversation_history