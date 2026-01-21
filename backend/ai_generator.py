import anthropic
from typing import List, Optional, Dict, Any

class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""
    
    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """You are an AI assistant specialized in course materials and educational content with access to tools for searching and exploring courses.

Available Tools:
1. search_course_content - Use for finding specific information, concepts, or answers within course materials
   - When users ask WHAT, HOW, or WHY questions about course topics
   - When users need detailed explanations or examples from lessons
   - Example queries: "How do I use prompt caching?", "What is tool use?", "Explain computer use"

2. get_course_outline - Use for getting course structure, lesson lists, or navigation
   - When users ask WHICH lessons, WHAT topics covered, or course STRUCTURE
   - When users want to see the table of contents or lesson overview
   - Example queries: "What lessons are in this course?", "Show me the course outline", "What topics does the MCP course cover?"
   - **IMPORTANT**: When using this tool, present the EXACT formatted output including ALL links - do not rewrite or synthesize

Tool Usage Rules:
- **You can make up to 2 sequential tool calls** to gather necessary information
- Use multiple calls when: comparing courses, following up on results, or building multi-part answers
- Choose the most appropriate tool(s) based on user intent
- For search_course_content: Synthesize results into accurate, fact-based responses
- For get_course_outline: Present the EXACT tool output preserving all formatting and links
- If a tool yields no results, you may try a different search or state this clearly

Sequential Tool Strategy:
- **Round 1**: Gather initial information or explore course structure
- **Round 2**: Refine search, compare results, or get additional context
- **After round 2**: Provide your final answer based on all gathered information
- Example flow: get_course_outline to find lesson topic → search_course_content with that topic

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without tools
- **Course-specific questions**: Use appropriate tool(s) first, then answer
- **Complex queries**: Use multiple tool calls to gather complete information
- **No meta-commentary**:
  - Provide direct answers only — no reasoning process, tool explanations, or question-type analysis
  - Do not mention "based on the search results" or "I used the outline tool"
  - Do not narrate your tool usage strategy

All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""
    
    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        
        # Pre-build base API parameters
        self.base_params = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 800
        }
    
    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None) -> str:
        """
        Generate AI response with optional tool usage and conversation context.
        
        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools
            
        Returns:
            Generated response as string
        """
        
        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history 
            else self.SYSTEM_PROMPT
        )
        
        # Prepare API call parameters efficiently
        api_params = {
            **self.base_params,
            "messages": [{"role": "user", "content": query}],
            "system": system_content
        }
        
        # Add tools if available
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}
        
        # Get response from Claude
        response = self.client.messages.create(**api_params)
        
        # Handle tool execution if needed
        if response.stop_reason == "tool_use" and tool_manager:
            return self._execute_tool_loop(response, api_params, tool_manager)

        # Return direct response
        return response.content[0].text

    def _execute_tool_loop(self, initial_response, base_params: Dict[str, Any], tool_manager):
        """
        Execute up to 2 rounds of sequential tool calling.

        Each round: execute tools → send results → get response → check for more tools
        Terminates when: (a) 2 rounds completed, (b) no tool_use in response, or (c) tool error

        Args:
            initial_response: The response containing tool use requests
            base_params: Base API parameters for initial call
            tool_manager: Manager to execute tools

        Returns:
            Final response text after tool execution
        """
        # Initialize context
        messages = base_params["messages"].copy()
        system_prompt = base_params["system"]
        tools = base_params.get("tools", [])
        current_response = initial_response
        max_rounds = 2
        current_round = 0

        # Loop for up to 2 rounds of tool execution
        while current_round < max_rounds:
            current_round += 1

            # Check if current response has tool_use blocks
            has_tool_use = any(
                block.type == "tool_use"
                for block in current_response.content
            )

            if not has_tool_use:
                # Claude provided final answer, no more tools needed
                break

            # Append Claude's tool use response
            messages.append({"role": "assistant", "content": current_response.content})

            # Execute all tool calls and collect results
            tool_results = []
            for content_block in current_response.content:
                if content_block.type == "tool_use":
                    try:
                        tool_result = tool_manager.execute_tool(
                            content_block.name,
                            **content_block.input
                        )
                    except Exception as e:
                        # On tool execution error, return error message
                        return f"Tool execution failed: {str(e)}"

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": content_block.id,
                        "content": tool_result
                    })

            # Append tool results
            if tool_results:
                messages.append({"role": "user", "content": tool_results})

            # Determine if tools should be included in next API call
            # Only include tools if we haven't reached max rounds
            include_tools = current_round < max_rounds

            # Build next API call parameters
            next_params = {
                **self.base_params,
                "messages": messages,
                "system": system_prompt
            }

            # Conditionally add tools
            if include_tools and tools:
                next_params["tools"] = tools
                next_params["tool_choice"] = {"type": "auto"}

            # Get next response
            current_response = self.client.messages.create(**next_params)

        # Return final response text
        return current_response.content[0].text