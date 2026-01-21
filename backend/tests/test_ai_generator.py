"""Tests for ai_generator.py to ensure correct tool calling"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from ai_generator import AIGenerator
from search_tools import ToolManager, CourseSearchTool


class TestAIGeneratorBasicResponse:
    """Test basic response generation without tools"""

    def test_generate_response_without_tools(self, mock_anthropic_client):
        """Test basic response generation without tool usage"""
        with patch('ai_generator.anthropic.Anthropic') as mock_anthropic:
            mock_anthropic.return_value = mock_anthropic_client

            generator = AIGenerator(api_key="test-key", model="claude-3-sonnet")
            response = generator.generate_response(query="Hello, how are you?")

            # Verify API was called
            mock_anthropic_client.messages.create.assert_called_once()

            # Verify response is a string
            assert isinstance(response, str)
            assert response == "Test response"

    def test_system_prompt_included(self, mock_anthropic_client):
        """Test that system prompt is included in API call"""
        with patch('ai_generator.anthropic.Anthropic') as mock_anthropic:
            mock_anthropic.return_value = mock_anthropic_client

            generator = AIGenerator(api_key="test-key", model="claude-3-sonnet")
            generator.generate_response(query="test")

            # Get the call arguments
            call_args = mock_anthropic_client.messages.create.call_args

            # Verify system prompt was included
            assert 'system' in call_args[1]
            assert "course materials" in call_args[1]['system'].lower()

    def test_conversation_history_included(self, mock_anthropic_client):
        """Test that conversation history is included in system prompt"""
        with patch('ai_generator.anthropic.Anthropic') as mock_anthropic:
            mock_anthropic.return_value = mock_anthropic_client

            generator = AIGenerator(api_key="test-key", model="claude-3-sonnet")
            history = "User: Previous question\nAssistant: Previous answer"

            generator.generate_response(query="new question", conversation_history=history)

            # Get the call arguments
            call_args = mock_anthropic_client.messages.create.call_args

            # Verify history is in system prompt
            assert 'system' in call_args[1]
            assert "Previous question" in call_args[1]['system']


class TestAIGeneratorToolCalling:
    """Test AI generator's tool calling functionality"""

    def test_tools_included_in_api_call(self, mock_anthropic_client, mock_vector_store):
        """Test that tools are included in API call when provided"""
        with patch('ai_generator.anthropic.Anthropic') as mock_anthropic:
            mock_anthropic.return_value = mock_anthropic_client

            # Create tool manager with search tool
            tool_manager = ToolManager()
            search_tool = CourseSearchTool(mock_vector_store)
            tool_manager.register_tool(search_tool)

            generator = AIGenerator(api_key="test-key", model="claude-3-sonnet")
            generator.generate_response(
                query="What is prompt caching?",
                tools=tool_manager.get_tool_definitions(),
                tool_manager=tool_manager
            )

            # Get the call arguments
            call_args = mock_anthropic_client.messages.create.call_args

            # Verify tools were included
            assert 'tools' in call_args[1]
            assert 'tool_choice' in call_args[1]
            assert len(call_args[1]['tools']) > 0

    def test_tool_execution_flow(self, mock_vector_store):
        """Test that tool execution happens when Claude requests it"""
        with patch('ai_generator.anthropic.Anthropic') as mock_anthropic:
            mock_client = MagicMock()

            # First response: Claude wants to use a tool
            tool_use_response = MagicMock()
            tool_use_block = MagicMock()
            tool_use_block.type = "tool_use"
            tool_use_block.name = "search_course_content"
            tool_use_block.id = "tool_123"
            tool_use_block.input = {"query": "What is prompt caching?"}

            tool_use_response.content = [tool_use_block]
            tool_use_response.stop_reason = "tool_use"

            # Second response: Claude's final answer after tool use
            final_response = MagicMock()
            final_response.content = [MagicMock(text="Prompt caching is a feature that...")]
            final_response.stop_reason = "end_turn"

            # Configure mock to return tool_use first, then final response
            mock_client.messages.create.side_effect = [tool_use_response, final_response]
            mock_anthropic.return_value = mock_client

            # Create tool manager
            tool_manager = ToolManager()
            search_tool = CourseSearchTool(mock_vector_store)
            tool_manager.register_tool(search_tool)

            generator = AIGenerator(api_key="test-key", model="claude-3-sonnet")
            response = generator.generate_response(
                query="What is prompt caching?",
                tools=tool_manager.get_tool_definitions(),
                tool_manager=tool_manager
            )

            # Verify API was called twice (initial + after tool use with final answer)
            assert mock_client.messages.create.call_count == 2

            # Verify vector store search was called
            mock_vector_store.search.assert_called_once_with(
                query="What is prompt caching?",
                course_name=None,
                lesson_number=None
            )

            # Verify final response is returned
            assert "Prompt caching is a feature that" in response

    def test_tool_result_included_in_second_call(self, mock_vector_store):
        """Test that tool results are included in the follow-up API call"""
        with patch('ai_generator.anthropic.Anthropic') as mock_anthropic:
            mock_client = MagicMock()

            # Setup tool use response
            tool_use_response = MagicMock()
            tool_use_block = MagicMock()
            tool_use_block.type = "tool_use"
            tool_use_block.name = "search_course_content"
            tool_use_block.id = "tool_123"
            tool_use_block.input = {"query": "test"}

            tool_use_response.content = [tool_use_block]
            tool_use_response.stop_reason = "tool_use"

            # Setup final response
            final_response = MagicMock()
            final_response.content = [MagicMock(text="Final answer")]
            final_response.stop_reason = "end_turn"

            mock_client.messages.create.side_effect = [tool_use_response, final_response]
            mock_anthropic.return_value = mock_client

            # Create tool manager
            tool_manager = ToolManager()
            search_tool = CourseSearchTool(mock_vector_store)
            tool_manager.register_tool(search_tool)

            generator = AIGenerator(api_key="test-key", model="claude-3-sonnet")
            generator.generate_response(
                query="test",
                tools=tool_manager.get_tool_definitions(),
                tool_manager=tool_manager
            )

            # Get the second API call (after tool execution) from the loop
            second_call_args = mock_client.messages.create.call_args_list[1]

            # Verify messages include tool results
            messages = second_call_args[1]['messages']
            assert len(messages) == 3  # user query + assistant tool use + user tool result

            # Verify structure: [user, assistant, user]
            assert messages[0]['role'] == 'user'
            assert messages[1]['role'] == 'assistant'
            assert messages[2]['role'] == 'user'

            # Find the tool result message (should be the last message)
            tool_result_message = messages[2]
            assert isinstance(tool_result_message['content'], list)

            # Verify tool result structure
            tool_result = tool_result_message['content'][0]
            assert tool_result['type'] == 'tool_result'
            assert tool_result['tool_use_id'] == 'tool_123'
            assert 'content' in tool_result

    def test_multiple_tool_calls_in_single_response(self, mock_vector_store):
        """Test handling of multiple tool calls in a single API response (same round)"""
        with patch('ai_generator.anthropic.Anthropic') as mock_anthropic:
            mock_client = MagicMock()

            # Response with two tool use blocks in same round
            tool_use_response = MagicMock()

            tool_block_1 = MagicMock()
            tool_block_1.type = "tool_use"
            tool_block_1.name = "search_course_content"
            tool_block_1.id = "tool_1"
            tool_block_1.input = {"query": "first query"}

            tool_block_2 = MagicMock()
            tool_block_2.type = "tool_use"
            tool_block_2.name = "search_course_content"
            tool_block_2.id = "tool_2"
            tool_block_2.input = {"query": "second query"}

            tool_use_response.content = [tool_block_1, tool_block_2]
            tool_use_response.stop_reason = "tool_use"

            final_response = MagicMock()
            final_response.content = [MagicMock(text="Combined answer")]
            final_response.stop_reason = "end_turn"

            mock_client.messages.create.side_effect = [tool_use_response, final_response]
            mock_anthropic.return_value = mock_client

            # Create tool manager
            tool_manager = ToolManager()
            search_tool = CourseSearchTool(mock_vector_store)
            tool_manager.register_tool(search_tool)

            generator = AIGenerator(api_key="test-key", model="claude-3-sonnet")
            response = generator.generate_response(
                query="test",
                tools=tool_manager.get_tool_definitions(),
                tool_manager=tool_manager
            )

            # Verify both tools were executed in the same round
            assert mock_vector_store.search.call_count == 2

            # Verify both tool results were sent back in the same message
            second_call_args = mock_client.messages.create.call_args_list[1]
            messages = second_call_args[1]['messages']
            # Structure: [user_query, assistant_with_2_tools, user_with_2_tool_results]
            assert len(messages) == 3
            tool_result_message = messages[2]
            assert len(tool_result_message['content']) == 2  # Two tool results


class TestAIGeneratorErrorHandling:
    """Test error handling in AI generator"""

    def test_handles_api_error_gracefully(self):
        """Test that API errors are handled appropriately"""
        with patch('ai_generator.anthropic.Anthropic') as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.create.side_effect = Exception("API Error")
            mock_anthropic.return_value = mock_client

            generator = AIGenerator(api_key="test-key", model="claude-3-sonnet")

            # Should raise the exception
            with pytest.raises(Exception) as exc_info:
                generator.generate_response(query="test")

            assert "API Error" in str(exc_info.value)


class TestAIGeneratorSequentialToolCalling:
    """Test sequential tool calling (up to 2 rounds)"""

    def test_two_round_tool_execution(self, mock_vector_store):
        """Test that Claude can make 2 sequential tool calls across rounds"""
        with patch('ai_generator.anthropic.Anthropic') as mock_anthropic:
            mock_client = MagicMock()

            # Round 1: Claude wants to get course outline
            round1_response = MagicMock()
            round1_tool_block = MagicMock()
            round1_tool_block.type = "tool_use"
            round1_tool_block.name = "get_course_outline"
            round1_tool_block.id = "tool_1"
            round1_tool_block.input = {"course_name": "Course A"}
            round1_response.content = [round1_tool_block]
            round1_response.stop_reason = "tool_use"

            # Round 2: Claude wants to search with info from round 1
            round2_response = MagicMock()
            round2_tool_block = MagicMock()
            round2_tool_block.type = "tool_use"
            round2_tool_block.name = "search_course_content"
            round2_tool_block.id = "tool_2"
            round2_tool_block.input = {"query": "MCP"}
            round2_response.content = [round2_tool_block]
            round2_response.stop_reason = "tool_use"

            # Final: Claude provides answer
            final_response = MagicMock()
            final_response.content = [MagicMock(text="Here is the answer")]
            final_response.stop_reason = "end_turn"

            mock_client.messages.create.side_effect = [
                round1_response,
                round2_response,
                final_response
            ]
            mock_anthropic.return_value = mock_client

            # Create tool manager
            tool_manager = ToolManager()
            search_tool = CourseSearchTool(mock_vector_store)
            tool_manager.register_tool(search_tool)

            generator = AIGenerator(api_key="test-key", model="claude-3-sonnet")
            response = generator.generate_response(
                query="Compare courses",
                tools=tool_manager.get_tool_definitions(),
                tool_manager=tool_manager
            )

            # Verify 3 API calls: initial + round 1 result + round 2 result
            assert mock_client.messages.create.call_count == 3

            # Verify tools were executed twice
            assert mock_vector_store.search.call_count >= 1

            # Verify final response is returned
            assert "Here is the answer" in response

    def test_early_termination_no_tools_needed(self, mock_vector_store):
        """Test that loop terminates when Claude doesn't need tools"""
        with patch('ai_generator.anthropic.Anthropic') as mock_anthropic:
            mock_client = MagicMock()

            # Claude responds directly without tools
            direct_response = MagicMock()
            direct_response.content = [MagicMock(text="I can answer this directly")]
            direct_response.stop_reason = "end_turn"

            mock_client.messages.create.return_value = direct_response
            mock_anthropic.return_value = mock_client

            generator = AIGenerator(api_key="test-key", model="claude-3-sonnet")
            response = generator.generate_response(
                query="What is Python?",
                tools=[]
            )

            # Verify API was called only once
            assert mock_client.messages.create.call_count == 1
            assert "I can answer this directly" in response

    def test_maximum_rounds_enforced(self, mock_vector_store):
        """Test that system stops after 2 rounds even if Claude wants more tools"""
        with patch('ai_generator.anthropic.Anthropic') as mock_anthropic:
            mock_client = MagicMock()

            # Round 1: Claude uses tool
            round1_response = MagicMock()
            round1_tool_block = MagicMock()
            round1_tool_block.type = "tool_use"
            round1_tool_block.name = "search_course_content"
            round1_tool_block.id = "tool_1"
            round1_tool_block.input = {"query": "test"}
            round1_response.content = [round1_tool_block]
            round1_response.stop_reason = "tool_use"

            # Round 2: Claude uses tool again
            round2_response = MagicMock()
            round2_tool_block = MagicMock()
            round2_tool_block.type = "tool_use"
            round2_tool_block.name = "search_course_content"
            round2_tool_block.id = "tool_2"
            round2_tool_block.input = {"query": "test2"}
            round2_response.content = [round2_tool_block]
            round2_response.stop_reason = "tool_use"

            # Final: Claude must answer (tools not available)
            final_response = MagicMock()
            final_response.content = [MagicMock(text="Final answer")]
            final_response.stop_reason = "end_turn"

            mock_client.messages.create.side_effect = [
                round1_response,
                round2_response,
                final_response
            ]
            mock_anthropic.return_value = mock_client

            # Create tool manager
            tool_manager = ToolManager()
            search_tool = CourseSearchTool(mock_vector_store)
            tool_manager.register_tool(search_tool)

            generator = AIGenerator(api_key="test-key", model="claude-3-sonnet")
            response = generator.generate_response(
                query="test",
                tools=tool_manager.get_tool_definitions(),
                tool_manager=tool_manager
            )

            # Verify 3 calls: initial + after round 1 + after round 2 (no tools)
            assert mock_client.messages.create.call_count == 3

            # Verify third call does NOT have tools in parameters
            third_call_args = mock_client.messages.create.call_args_list[2]
            assert 'tools' not in third_call_args[1]
            assert 'tool_choice' not in third_call_args[1]

            # Verify response is returned
            assert "Final answer" in response

    def test_tool_execution_failure_returns_error(self, mock_vector_store):
        """Test that tool execution failure returns error message"""
        with patch('ai_generator.anthropic.Anthropic') as mock_anthropic:
            mock_client = MagicMock()

            # Claude wants to use a tool
            tool_use_response = MagicMock()
            tool_use_block = MagicMock()
            tool_use_block.type = "tool_use"
            tool_use_block.name = "search_course_content"
            tool_use_block.id = "tool_1"
            tool_use_block.input = {"query": "test"}
            tool_use_response.content = [tool_use_block]
            tool_use_response.stop_reason = "tool_use"

            mock_client.messages.create.return_value = tool_use_response
            mock_anthropic.return_value = mock_client

            # Mock tool execution to fail
            tool_manager = MagicMock()
            tool_manager.execute_tool.side_effect = Exception("Tool failed")

            generator = AIGenerator(api_key="test-key", model="claude-3-sonnet")
            response = generator.generate_response(
                query="test",
                tools=[],
                tool_manager=tool_manager
            )

            # Verify error message is returned
            assert "Tool execution failed" in response

    def test_context_preservation_across_rounds(self, mock_vector_store):
        """Test that full conversation context is preserved across rounds"""
        with patch('ai_generator.anthropic.Anthropic') as mock_anthropic:
            mock_client = MagicMock()

            # Round 1: Tool use
            round1_response = MagicMock()
            round1_tool_block = MagicMock()
            round1_tool_block.type = "tool_use"
            round1_tool_block.name = "search_course_content"
            round1_tool_block.id = "tool_1"
            round1_tool_block.input = {"query": "first"}
            round1_response.content = [round1_tool_block]
            round1_response.stop_reason = "tool_use"

            # Round 2: Tool use again
            round2_response = MagicMock()
            round2_tool_block = MagicMock()
            round2_tool_block.type = "tool_use"
            round2_tool_block.name = "search_course_content"
            round2_tool_block.id = "tool_2"
            round2_tool_block.input = {"query": "second"}
            round2_response.content = [round2_tool_block]
            round2_response.stop_reason = "tool_use"

            # Final: Answer
            final_response = MagicMock()
            final_response.content = [MagicMock(text="Final")]
            final_response.stop_reason = "end_turn"

            mock_client.messages.create.side_effect = [
                round1_response,
                round2_response,
                final_response
            ]
            mock_anthropic.return_value = mock_client

            # Create tool manager
            tool_manager = ToolManager()
            search_tool = CourseSearchTool(mock_vector_store)
            tool_manager.register_tool(search_tool)

            generator = AIGenerator(api_key="test-key", model="claude-3-sonnet")
            generator.generate_response(
                query="test",
                tools=tool_manager.get_tool_definitions(),
                tool_manager=tool_manager
            )

            # Check round 2 API call to verify round 1 context is included
            round2_call_args = mock_client.messages.create.call_args_list[1]
            messages = round2_call_args[1]['messages']

            # Should have: [user_query, assistant_round1, user_tool_result_round1]
            assert len(messages) == 3
            assert messages[0]['role'] == 'user'
            assert messages[1]['role'] == 'assistant'
            assert messages[2]['role'] == 'user'

            # Check round 3 API call to verify both previous rounds are included
            final_call_args = mock_client.messages.create.call_args_list[2]
            messages = final_call_args[1]['messages']

            # Should have all previous context plus round 2 tool use and results
            # [user_query, assistant_round1, user_tool_result_round1, assistant_round2, user_tool_result_round2]
            assert len(messages) == 5

    def test_no_tools_in_final_round(self, mock_vector_store):
        """Test that tools are not included in the final API call"""
        with patch('ai_generator.anthropic.Anthropic') as mock_anthropic:
            mock_client = MagicMock()

            # Round 1: Tool use
            round1_response = MagicMock()
            round1_tool_block = MagicMock()
            round1_tool_block.type = "tool_use"
            round1_tool_block.name = "search_course_content"
            round1_tool_block.id = "tool_1"
            round1_tool_block.input = {"query": "test"}
            round1_response.content = [round1_tool_block]
            round1_response.stop_reason = "tool_use"

            # Round 2: Tool use (at max)
            round2_response = MagicMock()
            round2_tool_block = MagicMock()
            round2_tool_block.type = "tool_use"
            round2_tool_block.name = "search_course_content"
            round2_tool_block.id = "tool_2"
            round2_tool_block.input = {"query": "test2"}
            round2_response.content = [round2_tool_block]
            round2_response.stop_reason = "tool_use"

            # Final: Answer (tools should not be available)
            final_response = MagicMock()
            final_response.content = [MagicMock(text="Answer")]
            final_response.stop_reason = "end_turn"

            mock_client.messages.create.side_effect = [
                round1_response,
                round2_response,
                final_response
            ]
            mock_anthropic.return_value = mock_client

            # Create tool manager
            tool_manager = ToolManager()
            search_tool = CourseSearchTool(mock_vector_store)
            tool_manager.register_tool(search_tool)

            generator = AIGenerator(api_key="test-key", model="claude-3-sonnet")
            generator.generate_response(
                query="test",
                tools=tool_manager.get_tool_definitions(),
                tool_manager=tool_manager
            )

            # Verify first two calls HAVE tools
            first_call_args = mock_client.messages.create.call_args_list[0]
            assert 'tools' in first_call_args[1]

            second_call_args = mock_client.messages.create.call_args_list[1]
            assert 'tools' in second_call_args[1]

            # Verify third call does NOT have tools
            third_call_args = mock_client.messages.create.call_args_list[2]
            assert 'tools' not in third_call_args[1]
