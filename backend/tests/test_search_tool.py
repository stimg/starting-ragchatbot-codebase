"""Tests for CourseSearchTool.execute() method"""
import pytest
from unittest.mock import Mock, patch
from search_tools import CourseSearchTool, ToolManager
from vector_store import SearchResults


class TestCourseSearchToolExecute:
    """Test suite for CourseSearchTool.execute() method"""

    def test_basic_search_without_filters(self, mock_vector_store):
        """Test basic search returns formatted results"""
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="What is prompt caching?")

        # Verify search was called with correct parameters
        mock_vector_store.search.assert_called_once_with(
            query="What is prompt caching?",
            course_name=None,
            lesson_number=None
        )

        # Verify result is formatted correctly
        assert isinstance(result, str)
        assert "Building Towards Computer Use with Anthropic" in result
        assert "Welcome to the course" in result

    def test_search_with_course_name_filter(self, mock_vector_store):
        """Test search with course name filter"""
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(
            query="What is tool use?",
            course_name="Computer Use"
        )

        # Verify course_name was passed to search
        mock_vector_store.search.assert_called_once_with(
            query="What is tool use?",
            course_name="Computer Use",
            lesson_number=None
        )

        assert isinstance(result, str)

    def test_search_with_lesson_number_filter(self, mock_vector_store):
        """Test search with lesson number filter"""
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(
            query="API basics",
            lesson_number=1
        )

        # Verify lesson_number was passed to search
        mock_vector_store.search.assert_called_once_with(
            query="API basics",
            course_name=None,
            lesson_number=1
        )

        assert isinstance(result, str)

    def test_search_with_both_filters(self, mock_vector_store):
        """Test search with both course name and lesson number filters"""
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(
            query="How to use API?",
            course_name="Computer Use",
            lesson_number=1
        )

        # Verify both filters were passed
        mock_vector_store.search.assert_called_once_with(
            query="How to use API?",
            course_name="Computer Use",
            lesson_number=1
        )

        assert isinstance(result, str)

    def test_search_returns_error_message(self, mock_vector_store):
        """Test that error messages from vector store are returned"""
        # Configure mock to return error
        mock_vector_store.search.return_value = SearchResults(
            documents=[],
            metadata=[],
            distances=[],
            error="Database connection failed"
        )

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="test query")

        assert result == "Database connection failed"

    def test_search_returns_empty_results_message(self, mock_vector_store):
        """Test that empty results return appropriate message"""
        # Configure mock to return empty results
        mock_vector_store.search.return_value = SearchResults(
            documents=[],
            metadata=[],
            distances=[],
            error=None
        )

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="nonexistent topic")

        assert "No relevant content found" in result

    def test_empty_results_with_course_filter(self, mock_vector_store):
        """Test empty results message includes course name"""
        mock_vector_store.search.return_value = SearchResults(
            documents=[], metadata=[], distances=[], error=None
        )

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="test", course_name="Test Course")

        assert "No relevant content found" in result
        assert "Test Course" in result

    def test_empty_results_with_lesson_filter(self, mock_vector_store):
        """Test empty results message includes lesson number"""
        mock_vector_store.search.return_value = SearchResults(
            documents=[], metadata=[], distances=[], error=None
        )

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="test", lesson_number=5)

        assert "No relevant content found" in result
        assert "lesson 5" in result

    def test_result_formatting_includes_lesson_links(self, mock_vector_store):
        """Test that formatted results include lesson metadata"""
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="test")

        # Check formatting includes course title
        assert "[Building Towards Computer Use with Anthropic" in result
        # Check it includes lesson number
        assert "Lesson 0]" in result

    def test_last_sources_populated_after_search(self, mock_vector_store):
        """Test that last_sources is populated with search results"""
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="test")

        # Verify last_sources was populated
        assert len(tool.last_sources) > 0
        assert tool.last_sources[0]["text"] == "Building Towards Computer Use with Anthropic - Lesson 0"
        assert tool.last_sources[0]["link"] == "https://example.com/lesson0"

    def test_get_tool_definition(self):
        """Test that tool definition is correctly formed"""
        mock_store = Mock()
        tool = CourseSearchTool(mock_store)

        definition = tool.get_tool_definition()

        assert definition["name"] == "search_course_content"
        assert "description" in definition
        assert "input_schema" in definition
        assert definition["input_schema"]["required"] == ["query"]

        # Check optional parameters
        properties = definition["input_schema"]["properties"]
        assert "query" in properties
        assert "course_name" in properties
        assert "lesson_number" in properties


class TestToolManager:
    """Test suite for ToolManager"""

    def test_register_tool(self, mock_vector_store):
        """Test that tools can be registered"""
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)

        manager.register_tool(tool)

        assert "search_course_content" in manager.tools

    def test_get_tool_definitions(self, mock_vector_store):
        """Test that tool definitions are returned correctly"""
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(tool)

        definitions = manager.get_tool_definitions()

        assert len(definitions) == 1
        assert definitions[0]["name"] == "search_course_content"

    def test_execute_tool(self, mock_vector_store):
        """Test that tools can be executed by name"""
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(tool)

        result = manager.execute_tool(
            "search_course_content",
            query="test query"
        )

        assert isinstance(result, str)
        mock_vector_store.search.assert_called_once()

    def test_execute_nonexistent_tool(self):
        """Test that executing nonexistent tool returns error"""
        manager = ToolManager()

        result = manager.execute_tool("nonexistent_tool", query="test")

        assert "not found" in result

    def test_get_last_sources(self, mock_vector_store):
        """Test that last sources can be retrieved"""
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(tool)

        # Execute a search
        manager.execute_tool("search_course_content", query="test")

        # Get sources
        sources = manager.get_last_sources()

        assert len(sources) > 0
        assert "text" in sources[0]
        assert "link" in sources[0]

    def test_reset_sources(self, mock_vector_store):
        """Test that sources can be reset"""
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(tool)

        # Execute search and verify sources exist
        manager.execute_tool("search_course_content", query="test")
        assert len(manager.get_last_sources()) > 0

        # Reset sources
        manager.reset_sources()

        # Verify sources are cleared
        assert len(manager.get_last_sources()) == 0
