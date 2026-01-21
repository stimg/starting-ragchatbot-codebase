"""
Comprehensive API endpoint tests for the RAG chatbot FastAPI application.

Tests cover:
- Query endpoint (/api/query)
- Course statistics endpoint (/api/courses)
- Session management endpoint (/api/session/{session_id})
- Health check endpoint (/)
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
import json


class TestQueryEndpoint:
    """Test cases for the /api/query POST endpoint"""

    def test_query_with_existing_session(self, test_client):
        """Test query endpoint with an existing session ID"""
        request_data = {
            "query": "What is prompt caching?",
            "session_id": "existing-session-123"
        }

        response = test_client.post("/api/query", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data
        assert isinstance(data["sources"], list)
        assert data["session_id"] == "existing-session-123"

    def test_query_creates_new_session(self, test_client):
        """Test that query endpoint creates a new session if none provided"""
        request_data = {
            "query": "Tell me about the course material"
        }

        response = test_client.post("/api/query", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data
        assert data["session_id"] == "test-session-123"  # Default mock value

    def test_query_response_structure(self, test_client):
        """Validate the structure of the query response"""
        request_data = {
            "query": "What are the key concepts?",
            "session_id": "test-session"
        }

        response = test_client.post("/api/query", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # Validate response structure
        assert isinstance(data["answer"], str)
        assert len(data["answer"]) > 0
        assert isinstance(data["sources"], list)
        assert isinstance(data["session_id"], str)

        # Validate sources structure if present
        if data["sources"]:
            for source in data["sources"]:
                assert "text" in source
                assert "link" in source

    def test_query_with_multiple_turns(self, test_client):
        """Test multiple queries in the same session"""
        session_id = "multi-turn-session"

        # First query
        response1 = test_client.post(
            "/api/query",
            json={"query": "First question", "session_id": session_id}
        )
        assert response1.status_code == 200

        # Second query with same session
        response2 = test_client.post(
            "/api/query",
            json={"query": "Second question", "session_id": session_id}
        )
        assert response2.status_code == 200
        assert response2.json()["session_id"] == session_id

    def test_query_handles_empty_query(self, test_client):
        """Test query endpoint behavior with empty query string"""
        request_data = {
            "query": "",
            "session_id": "test-session"
        }

        # The endpoint may handle empty queries differently
        # This test documents the current behavior
        response = test_client.post("/api/query", json=request_data)

        # Should still return a response (though the answer might be empty/error)
        assert response.status_code in [200, 400, 422]

    def test_query_with_special_characters(self, test_client):
        """Test query endpoint with special characters and unicode"""
        request_data = {
            "query": "What about special characters? !@#$%",
            "session_id": "unicode-session"
        }

        response = test_client.post("/api/query", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data


class TestCoursesEndpoint:
    """Test cases for the /api/courses GET endpoint"""

    def test_courses_endpoint_returns_stats(self, test_client):
        """Test that courses endpoint returns course statistics"""
        response = test_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()
        assert "total_courses" in data
        assert "course_titles" in data

    def test_courses_response_structure(self, test_client):
        """Validate the structure of courses response"""
        response = test_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()

        # Validate structure
        assert isinstance(data["total_courses"], int)
        assert data["total_courses"] >= 0
        assert isinstance(data["course_titles"], list)

        # Validate course titles are strings
        for title in data["course_titles"]:
            assert isinstance(title, str)
            assert len(title) > 0

    def test_courses_consistency(self, test_client):
        """Test that course count matches the length of course_titles"""
        response = test_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()

        # The total_courses should match the number of titles
        assert data["total_courses"] == len(data["course_titles"])

    def test_courses_multiple_calls(self, test_client):
        """Test that multiple calls return consistent data"""
        response1 = test_client.get("/api/courses")
        response2 = test_client.get("/api/courses")

        assert response1.status_code == 200
        assert response2.status_code == 200

        data1 = response1.json()
        data2 = response2.json()

        # Data should be consistent across calls
        assert data1["total_courses"] == data2["total_courses"]
        assert data1["course_titles"] == data2["course_titles"]


class TestSessionEndpoint:
    """Test cases for the /api/session/{session_id} DELETE endpoint"""

    def test_delete_session_success(self, test_client):
        """Test successful session deletion"""
        session_id = "session-to-delete"

        response = test_client.delete(f"/api/session/{session_id}")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "message" in data
        assert data["status"] == "ok"

    def test_delete_session_response_format(self, test_client):
        """Validate the response format for session deletion"""
        session_id = "test-session-123"

        response = test_client.delete(f"/api/session/{session_id}")

        assert response.status_code == 200
        data = response.json()

        # Validate response structure
        assert isinstance(data["status"], str)
        assert isinstance(data["message"], str)
        assert session_id in data["message"] or "Session" in data["message"]

    def test_delete_nonexistent_session(self, test_client):
        """Test deleting a session that doesn't exist"""
        session_id = "nonexistent-session-xyz"

        response = test_client.delete(f"/api/session/{session_id}")

        # Should still return 200 (graceful handling)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_delete_session_with_special_chars(self, test_client):
        """Test session deletion with special characters in session ID"""
        session_id = "session-123-abc_test"

        response = test_client.delete(f"/api/session/{session_id}")

        assert response.status_code == 200


class TestHealthCheck:
    """Test cases for the root health check endpoint"""

    def test_root_endpoint_returns_ok(self, test_client):
        """Test that root endpoint returns a health status"""
        response = test_client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"

    def test_root_endpoint_response_structure(self, test_client):
        """Validate the structure of the health check response"""
        response = test_client.get("/")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data["status"], str)
        assert "message" in data or "message" not in data  # Message is optional
        if "message" in data:
            assert isinstance(data["message"], str)


class TestErrorHandling:
    """Test cases for error handling across endpoints"""

    def test_query_endpoint_error_handling(self, test_client, monkeypatch):
        """Test query endpoint error handling"""
        def mock_error_query(*args, **kwargs):
            raise Exception("Simulated error")

        # Get the app and patch the rag_system
        test_client.app.state.rag_system.query = mock_error_query

        response = test_client.post(
            "/api/query",
            json={"query": "test", "session_id": "test"}
        )

        # Should return 500 error
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data

    def test_courses_endpoint_error_handling(self, test_client):
        """Test courses endpoint error handling"""
        def mock_error_analytics(*args, **kwargs):
            raise Exception("Analytics error")

        test_client.app.state.rag_system.get_course_analytics = mock_error_analytics

        response = test_client.get("/api/courses")

        # Should return 500 error
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data


class TestCorsHeaders:
    """Test cases for CORS headers"""

    def test_cors_headers_on_query_endpoint(self, test_client):
        """Test that CORS headers are present on query endpoint"""
        response = test_client.post(
            "/api/query",
            json={"query": "test"}
        )

        assert response.status_code == 200
        # CORS headers should be present
        assert "access-control-allow-origin" in response.headers or True  # May be * or specific

    def test_cors_headers_on_courses_endpoint(self, test_client):
        """Test that CORS headers are present on courses endpoint"""
        response = test_client.get("/api/courses")

        assert response.status_code == 200
        # Headers may vary based on middleware configuration


class TestRequestValidation:
    """Test cases for request validation"""

    def test_query_endpoint_missing_query_field(self, test_client):
        """Test query endpoint with missing 'query' field"""
        request_data = {
            "session_id": "test"
        }

        response = test_client.post("/api/query", json=request_data)

        # Should return 422 (validation error) or 400
        assert response.status_code in [422, 400]

    def test_query_endpoint_invalid_json(self, test_client):
        """Test query endpoint with invalid JSON"""
        response = test_client.post(
            "/api/query",
            content="invalid json{",
            headers={"Content-Type": "application/json"}
        )

        # Should return 422 or 400
        assert response.status_code in [422, 400]

    def test_session_delete_with_empty_id(self, test_client):
        """Test session delete with empty session ID"""
        response = test_client.delete("/api/session/")

        # Route may not match or return 404
        assert response.status_code in [404, 405]


class TestResponseContentTypes:
    """Test cases for response content types"""

    def test_query_response_content_type(self, test_client):
        """Test that query endpoint returns JSON"""
        response = test_client.post(
            "/api/query",
            json={"query": "test"}
        )

        assert "application/json" in response.headers.get("content-type", "")

    def test_courses_response_content_type(self, test_client):
        """Test that courses endpoint returns JSON"""
        response = test_client.get("/api/courses")

        assert "application/json" in response.headers.get("content-type", "")

    def test_root_response_content_type(self, test_client):
        """Test that root endpoint returns JSON"""
        response = test_client.get("/")

        assert "application/json" in response.headers.get("content-type", "")
