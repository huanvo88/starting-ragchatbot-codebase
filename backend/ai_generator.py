import anthropic
import ollama
import json
from typing import List, Optional, Dict, Any

class AIGenerator:
    """Handles interactions with AI models (Anthropic Claude or local Ollama) for generating responses"""
    
    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to comprehensive search and outline tools for course information.

Tool Usage Guidelines:
- **Course content search tool**: Use for questions about specific course content or detailed educational materials
- **Course outline tool**: Use for questions about course structure, lesson lists, or course overviews
- **One tool use per query maximum**
- Synthesize tool results into accurate, fact-based responses
- If tools yield no results, state this clearly without offering alternatives

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without using tools
- **Course-specific content questions**: Use search tool first, then answer
- **Course outline/structure questions**: Use outline tool to provide course title, course link, and complete lesson list with numbers and titles
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, tool explanations, or question-type analysis
 - Do not mention "based on the search results" or "using the tool"

All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""
    
    def __init__(self, provider: str, api_key: str = "", model: str = "", ollama_base_url: str = "http://localhost:11434"):
        self.provider = provider.lower()
        self.model = model
        
        if self.provider == "anthropic":
            self.client = anthropic.Anthropic(api_key=api_key)
            self.base_params = {
                "model": self.model,
                "temperature": 0,
                "max_tokens": 800
            }
        elif self.provider == "ollama":
            self.ollama_client = ollama.Client(host=ollama_base_url)
            self.base_params = {
                "model": self.model,
                "options": {
                    "temperature": 0,
                    "num_predict": 800
                }
            }
        else:
            raise ValueError(f"Unsupported AI provider: {provider}")
    
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
        
        if self.provider == "anthropic":
            return self._generate_anthropic_response(api_params, tools, tool_manager)
        elif self.provider == "ollama":
            return self._generate_ollama_response(query, system_content, tools, tool_manager)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    def _handle_tool_execution(self, initial_response, base_params: Dict[str, Any], tool_manager):
        """
        Handle execution of tool calls and get follow-up response.
        
        Args:
            initial_response: The response containing tool use requests
            base_params: Base API parameters
            tool_manager: Manager to execute tools
            
        Returns:
            Final response text after tool execution
        """
        # Start with existing messages
        messages = base_params["messages"].copy()
        
        # Add AI's tool use response
        messages.append({"role": "assistant", "content": initial_response.content})
        
        # Execute all tool calls and collect results
        tool_results = []
        for content_block in initial_response.content:
            if content_block.type == "tool_use":
                tool_result = tool_manager.execute_tool(
                    content_block.name, 
                    **content_block.input
                )
                
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": content_block.id,
                    "content": tool_result
                })
        
        # Add tool results as single message
        if tool_results:
            messages.append({"role": "user", "content": tool_results})
        
        # Prepare final API call without tools
        final_params = {
            **self.base_params,
            "messages": messages,
            "system": base_params["system"]
        }
        
        # Get final response
        final_response = self.client.messages.create(**final_params)
        return final_response.content[0].text
    
    def _generate_anthropic_response(self, api_params: Dict[str, Any], tools: Optional[List], tool_manager) -> str:
        """Generate response using Anthropic Claude"""
        # Get response from Claude
        response = self.client.messages.create(**api_params)
        
        # Handle tool execution if needed
        if response.stop_reason == "tool_use" and tool_manager:
            return self._handle_tool_execution(response, api_params, tool_manager)
        
        # Return direct response
        return response.content[0].text
    
    def _generate_ollama_response(self, query: str, system_content: str, tools: Optional[List], tool_manager) -> str:
        """Generate response using local Ollama model"""
        # For Ollama, we need to handle tools differently since it doesn't have native tool calling
        # We'll use a simplified approach: if tools are available, we'll ask the model to decide
        
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": query}
        ]
        
        # Add tool information to the prompt if tools are available
        if tools and tool_manager:
            # Simple tool handling for Ollama - check if search is needed
            search_keywords = ["course", "lesson", "instructor", "content", "material", "chapter", "topic"]
            query_lower = query.lower()
            
            if any(keyword in query_lower for keyword in search_keywords):
                # Execute search tool
                try:
                    search_result = tool_manager.execute_tool("search_course_content", query=query)
                    enhanced_query = f"{query}\n\nRelevant course content:\n{search_result}"
                    messages[-1]["content"] = enhanced_query
                except Exception as e:
                    print(f"Search tool error: {e}")
        
        # Generate response with Ollama
        response = self.ollama_client.chat(
            model=self.model,
            messages=messages,
            options=self.base_params["options"]
        )
        
        return response['message']['content']
    
    def generate_response_stream(self, query: str,
                                conversation_history: Optional[str] = None,
                                tools: Optional[List] = None,
                                tool_manager=None):
        """
        Generate streaming AI response with optional tool usage and conversation context.
        
        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools
            
        Yields:
            Dict chunks with response data
        """
        
        # Build system content efficiently
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history 
            else self.SYSTEM_PROMPT
        )
        
        if self.provider == "anthropic":
            yield from self._generate_anthropic_response_stream(query, system_content, tools, tool_manager)
        elif self.provider == "ollama":
            yield from self._generate_ollama_response_stream(query, system_content, tools, tool_manager)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    def _generate_anthropic_response_stream(self, query: str, system_content: str, tools: Optional[List], tool_manager):
        """Generate streaming response using Anthropic Claude"""
        # Anthropic doesn't have native streaming with tools, so we'll use the regular method
        # and yield the complete response
        api_params = {
            **self.base_params,
            "messages": [{"role": "user", "content": query}],
            "system": system_content
        }
        
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}
        
        response = self.client.messages.create(**api_params)
        
        if response.stop_reason == "tool_use" and tool_manager:
            final_response = self._handle_tool_execution(response, api_params, tool_manager)
            yield {"type": "content", "content": final_response}
        else:
            yield {"type": "content", "content": response.content[0].text}
        
        # Get sources after response
        if tool_manager:
            sources = tool_manager.get_last_sources()
            if sources:
                yield {"type": "sources", "sources": sources}
            tool_manager.reset_sources()
    
    def _generate_ollama_response_stream(self, query: str, system_content: str, tools: Optional[List], tool_manager):
        """Generate streaming response using local Ollama model"""
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": query}
        ]
        
        # Handle tools for Ollama
        if tools and tool_manager:
            search_keywords = ["course", "lesson", "instructor", "content", "material", "chapter", "topic"]
            query_lower = query.lower()
            
            if any(keyword in query_lower for keyword in search_keywords):
                try:
                    search_result = tool_manager.execute_tool("search_course_content", query=query)
                    enhanced_query = f"{query}\n\nRelevant course content:\n{search_result}"
                    messages[-1]["content"] = enhanced_query
                    
                    # Yield sources
                    sources = tool_manager.get_last_sources()
                    if sources:
                        yield {"type": "sources", "sources": sources}
                    tool_manager.reset_sources()
                except Exception as e:
                    print(f"Search tool error: {e}")
        
        # Stream response from Ollama
        try:
            stream = self.ollama_client.chat(
                model=self.model,
                messages=messages,
                options=self.base_params["options"],
                stream=True
            )
            
            for chunk in stream:
                if 'message' in chunk and 'content' in chunk['message']:
                    content = chunk['message']['content']
                    if content:
                        yield {"type": "content", "content": content}
        except Exception as e:
            yield {"type": "content", "content": f"Error: {str(e)}"}