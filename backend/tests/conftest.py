"""Shared pytest fixtures for testing"""
import pytest
import sys
import os
from unittest.mock import Mock, MagicMock, patch
from typing import List, Dict, Any
import tempfile
import shutil

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


# ==================== API Testing Fixtures ====================

@pytest.fixture
def temp_db_path():
    """Create and cleanup a temporary database directory for testing"""
    temp_dir = tempfile.mkdtemp(prefix="test_chroma_")
    yield temp_dir
    # Cleanup after test
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


@pytest.fixture
def test_app():
    """Create a test FastAPI application without static file mounting"""
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.middleware.trustedhost import TrustedHostMiddleware
    from pydantic import BaseModel
    from typing import Optional

    # Create a minimal test app with API endpoints only (no static files)
    app = FastAPI(title="Test RAG System")

    # Add middleware
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request/Response models
    class QueryRequest(BaseModel):
        query: str
        session_id: Optional[str] = None

    class QueryResponse(BaseModel):
        answer: str
        sources: List[dict]
        session_id: str

    class CourseStats(BaseModel):
        total_courses: int
        course_titles: List[str]

    # Mock RAG system
    mock_rag_system = MagicMock()
    mock_rag_system.session_manager = MagicMock()
    mock_rag_system.session_manager.create_session.return_value = "test-session-123"
    mock_rag_system.query.return_value = (
        "This is a test answer",
        [{"text": "Source 1", "link": "https://example.com/1"}]
    )
    mock_rag_system.get_course_analytics.return_value = {
        "total_courses": 2,
        "course_titles": ["Course 1", "Course 2"]
    }

    # Inject mock into app
    app.state.rag_system = mock_rag_system

    # API Endpoints
    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        """Process a query and return response with sources"""
        try:
            session_id = request.session_id or app.state.rag_system.session_manager.create_session()
            answer, sources = app.state.rag_system.query(request.query, session_id)

            return QueryResponse(
                answer=answer,
                sources=sources,
                session_id=session_id
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        """Get course analytics and statistics"""
        try:
            analytics = app.state.rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.delete("/api/session/{session_id}")
    async def delete_session(session_id: str):
        """Delete a conversation session"""
        try:
            app.state.rag_system.session_manager.clear_session(session_id)
            return {"status": "ok", "message": f"Session {session_id} cleared"}
        except Exception:
            return {"status": "ok", "message": "Session already cleared or not found"}

    @app.get("/")
    async def root():
        """Health check endpoint"""
        return {"status": "ok", "message": "RAG System API is running"}

    return app


@pytest.fixture
def test_client(test_app):
    """Create a FastAPI test client"""
    from fastapi.testclient import TestClient
    return TestClient(test_app)


@pytest.fixture
def mock_rag_system():
    """Create a mock RAG system for API testing"""
    mock_rag = MagicMock()

    # Mock session manager
    mock_rag.session_manager = MagicMock()
    mock_rag.session_manager.create_session.return_value = "test-session-123"
    mock_rag.session_manager.clear_session.return_value = None

    # Mock query method
    mock_rag.query.return_value = (
        "This is a test answer about the course material",
        [
            {
                "text": "The course covers API basics and authentication",
                "link": "https://example.com/lesson1"
            },
            {
                "text": "You can use tools to extend Claude's capabilities",
                "link": "https://example.com/lesson2"
            }
        ]
    )

    # Mock analytics
    mock_rag.get_course_analytics.return_value = {
        "total_courses": 3,
        "course_titles": [
            "Building Towards Computer Use",
            "API Mastery",
            "Advanced Prompting"
        ]
    }

    # Mock add_course_folder
    mock_rag.add_course_folder.return_value = (2, 150)

    return mock_rag


@pytest.fixture
def api_request_samples():
    """Provide sample API requests for testing"""
    return {
        "valid_query": {
            "query": "What is prompt caching?",
            "session_id": "test-session-123"
        },
        "new_session_query": {
            "query": "Tell me about the course"
        },
        "empty_query": {
            "query": ""
        }
    }


@pytest.fixture
def expected_api_responses():
    """Provide expected API response structures for validation"""
    return {
        "query_response": {
            "answer": str,
            "sources": list,
            "session_id": str
        },
        "course_stats": {
            "total_courses": int,
            "course_titles": list
        },
        "session_delete": {
            "status": str,
            "message": str
        },
        "health_check": {
            "status": str,
            "message": str
        }
    }
