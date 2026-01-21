"""Shared pytest fixtures for testing"""
import pytest
import sys
import os
from unittest.mock import Mock, MagicMock
from typing import List, Dict, Any

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models import Course, Lesson, CourseChunk
from vector_store import VectorStore, SearchResults
from search_tools import CourseSearchTool, ToolManager
from config import Config


@pytest.fixture
def sample_course():
    """Create a sample course for testing"""
    return Course(
        title="Building Towards Computer Use with Anthropic",
        course_link="https://example.com/course1",
        instructor="Colt Steele",
        lessons=[
            Lesson(
                lesson_number=0,
                title="Introduction",
                lesson_link="https://example.com/lesson0"
            ),
            Lesson(
                lesson_number=1,
                title="API Basics",
                lesson_link="https://example.com/lesson1"
            )
        ]
    )


@pytest.fixture
def sample_chunks():
    """Create sample course chunks for testing"""
    return [
        CourseChunk(
            content="Lesson 0 content: Welcome to the course about computer use and AI.",
            course_title="Building Towards Computer Use with Anthropic",
            lesson_number=0,
            chunk_index=0
        ),
        CourseChunk(
            content="This course covers prompt caching and tool use with Claude.",
            course_title="Building Towards Computer Use with Anthropic",
            lesson_number=0,
            chunk_index=1
        ),
        CourseChunk(
            content="Lesson 1 content: Learn how to use the Anthropic API.",
            course_title="Building Towards Computer Use with Anthropic",
            lesson_number=1,
            chunk_index=2
        )
    ]


@pytest.fixture
def mock_vector_store():
    """Create a mock vector store"""
    mock_store = Mock(spec=VectorStore)

    # Default successful search response
    mock_store.search.return_value = SearchResults(
        documents=[
            "Welcome to the course about computer use and AI.",
            "This course covers prompt caching and tool use."
        ],
        metadata=[
            {
                "course_title": "Building Towards Computer Use with Anthropic",
                "lesson_number": 0,
                "chunk_index": 0
            },
            {
                "course_title": "Building Towards Computer Use with Anthropic",
                "lesson_number": 0,
                "chunk_index": 1
            }
        ],
        distances=[0.1, 0.2],
        error=None
    )

    # Mock get_lesson_link
    mock_store.get_lesson_link.return_value = "https://example.com/lesson0"

    return mock_store


@pytest.fixture
def mock_anthropic_client():
    """Create a mock Anthropic client"""
    mock_client = MagicMock()

    # Mock basic text response
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Test response")]
    mock_response.stop_reason = "end_turn"

    mock_client.messages.create.return_value = mock_response

    return mock_client


@pytest.fixture
def test_config():
    """Create a test configuration"""
    config = Config()
    config.CHUNK_SIZE = 800
    config.CHUNK_OVERLAP = 100
    config.MAX_RESULTS = 5  # Override the problematic 0 value
    config.CHROMA_PATH = "./test_chroma_db"
    return config
