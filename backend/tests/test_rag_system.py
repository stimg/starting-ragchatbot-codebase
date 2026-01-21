"""Integration tests for RAG system query handling"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from rag_system import RAGSystem
from config import Config


class TestRAGSystemIntegration:
    """Integration tests for the RAG system"""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration"""
        config = Mock(spec=Config)
        config.CHUNK_SIZE = 800
        config.CHUNK_OVERLAP = 100
        config.MAX_RESULTS = 5  # CRITICAL: Not 0!
        config.CHROMA_PATH = "./test_chroma"
        config.EMBEDDING_MODEL = "all-MiniLM-L6-v2"
        config.ANTHROPIC_API_KEY = "test-key"
        config.ANTHROPIC_MODEL = "claude-3-sonnet"
        config.MAX_HISTORY = 2
        return config

    def test_rag_system_initialization(self, mock_config):
        """Test that RAG system initializes all components"""
        with patch('rag_system.VectorStore'), \
             patch('rag_system.AIGenerator'), \
             patch('rag_system.SessionManager'), \
             patch('rag_system.DocumentProcessor'):

            rag = RAGSystem(mock_config)

            # Verify all components are initialized
            assert rag.document_processor is not None
            assert rag.vector_store is not None
            assert rag.ai_generator is not None
            assert rag.session_manager is not None
            assert rag.tool_manager is not None
            assert rag.search_tool is not None

    def test_query_calls_ai_generator_with_tools(self, mock_config):
        """Test that query method calls AI generator with tools"""
        with patch('rag_system.VectorStore') as mock_vs, \
             patch('rag_system.AIGenerator') as mock_ai, \
             patch('rag_system.SessionManager') as mock_sm, \
             patch('rag_system.DocumentProcessor'):

            # Setup mocks
            mock_ai_instance = MagicMock()
            mock_ai_instance.generate_response.return_value = "Test answer"
            mock_ai.return_value = mock_ai_instance

            mock_sm_instance = MagicMock()
            mock_sm_instance.get_conversation_history.return_value = None
            mock_sm.return_value = mock_sm_instance

            # Create RAG system
            rag = RAGSystem(mock_config)

            # Execute query
            response, sources = rag.query("What is prompt caching?")

            # Verify AI generator was called with tools
            mock_ai_instance.generate_response.assert_called_once()
            call_args = mock_ai_instance.generate_response.call_args[1]

            assert 'tools' in call_args
            assert 'tool_manager' in call_args
            assert call_args['tools'] is not None
            assert call_args['tool_manager'] is not None

            # Verify response is returned
            assert response == "Test answer"

    def test_query_with_session_id(self, mock_config):
        """Test query with session ID retrieves conversation history"""
        with patch('rag_system.VectorStore'), \
             patch('rag_system.AIGenerator') as mock_ai, \
             patch('rag_system.SessionManager') as mock_sm, \
             patch('rag_system.DocumentProcessor'):

            # Setup mocks
            mock_ai_instance = MagicMock()
            mock_ai_instance.generate_response.return_value = "Answer"
            mock_ai.return_value = mock_ai_instance

            mock_sm_instance = MagicMock()
            mock_sm_instance.get_conversation_history.return_value = "Previous conversation"
            mock_sm.return_value = mock_sm_instance

            # Create RAG system
            rag = RAGSystem(mock_config)

            # Execute query with session
            response, sources = rag.query("Follow-up question", session_id="session123")

            # Verify history was retrieved
            mock_sm_instance.get_conversation_history.assert_called_once_with("session123")

            # Verify history was passed to AI generator
            call_args = mock_ai_instance.generate_response.call_args[1]
            assert call_args['conversation_history'] == "Previous conversation"

    def test_query_updates_session_history(self, mock_config):
        """Test that query updates conversation history"""
        with patch('rag_system.VectorStore'), \
             patch('rag_system.AIGenerator') as mock_ai, \
             patch('rag_system.SessionManager') as mock_sm, \
             patch('rag_system.DocumentProcessor'):

            # Setup mocks
            mock_ai_instance = MagicMock()
            mock_ai_instance.generate_response.return_value = "Answer"
            mock_ai.return_value = mock_ai_instance

            mock_sm_instance = MagicMock()
            mock_sm_instance.get_conversation_history.return_value = None
            mock_sm.return_value = mock_sm_instance

            # Create RAG system
            rag = RAGSystem(mock_config)

            # Execute query
            query_text = "What is prompt caching?"
            response, sources = rag.query(query_text, session_id="session123")

            # Verify session was updated with the original query, not the prompt
            mock_sm_instance.add_exchange.assert_called_once_with(
                "session123",
                query_text,
                "Answer"
            )

    def test_query_returns_sources_from_tool_manager(self, mock_config):
        """Test that sources from tool execution are returned"""
        with patch('rag_system.VectorStore') as mock_vs, \
             patch('rag_system.AIGenerator') as mock_ai, \
             patch('rag_system.SessionManager') as mock_sm, \
             patch('rag_system.DocumentProcessor'):

            # Setup vector store mock
            from vector_store import SearchResults
            mock_vs_instance = MagicMock()
            mock_vs_instance.search.return_value = SearchResults(
                documents=["Test content"],
                metadata=[{"course_title": "Test Course", "lesson_number": 1}],
                distances=[0.1],
                error=None
            )
            mock_vs_instance.get_lesson_link.return_value = "https://example.com/lesson1"
            mock_vs.return_value = mock_vs_instance

            # Setup AI generator mock
            mock_ai_instance = MagicMock()
            mock_ai_instance.generate_response.return_value = "Answer"
            mock_ai.return_value = mock_ai_instance

            # Setup session manager mock
            mock_sm_instance = MagicMock()
            mock_sm.return_value = mock_sm_instance

            # Create RAG system
            rag = RAGSystem(mock_config)

            # Manually trigger a tool execution to populate sources
            rag.tool_manager.execute_tool("search_course_content", query="test")

            # Execute query
            response, sources = rag.query("test")

            # Verify sources are returned
            assert len(sources) > 0
            assert sources[0]["text"] == "Test Course - Lesson 1"


class TestRAGSystemWithRealVectorStore:
    """Test RAG system with actual vector store (but mocked embeddings)"""

    @pytest.fixture
    def rag_with_real_store(self, tmp_path, test_config):
        """Create RAG system with real vector store in temp directory"""
        # Override chroma path to temp directory
        test_config.CHROMA_PATH = str(tmp_path / "test_chroma")

        with patch('rag_system.AIGenerator') as mock_ai, \
             patch('rag_system.SessionManager') as mock_sm:

            # Setup AI generator mock
            mock_ai_instance = MagicMock()
            mock_ai_instance.generate_response.return_value = "Test answer"
            mock_ai.return_value = mock_ai_instance

            # Setup session manager mock
            mock_sm_instance = MagicMock()
            mock_sm_instance.get_conversation_history.return_value = None
            mock_sm.return_value = mock_sm_instance

            # Create RAG system (will create real vector store)
            rag = RAGSystem(test_config)

            return rag

    def test_max_results_configuration(self, tmp_path):
        """CRITICAL TEST: Verify MAX_RESULTS is not 0"""
        config = Config()

        # This is the bug: MAX_RESULTS defaults to 0
        # This test will FAIL if the bug exists
        assert config.MAX_RESULTS != 0, \
            "CRITICAL BUG: MAX_RESULTS is 0, which causes empty search results!"

    def test_vector_store_validates_zero_max_results(self, tmp_path):
        """Test that VectorStore rejects max_results=0 with validation"""
        from vector_store import VectorStore
        import pytest

        # Attempting to create vector store with max_results=0 should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            store = VectorStore(
                chroma_path=str(tmp_path / "test_chroma"),
                embedding_model="all-MiniLM-L6-v2",
                max_results=0  # This should be rejected!
            )

        # Verify the error message is helpful
        assert "max_results must be positive" in str(exc_info.value)
        assert "0" in str(exc_info.value)


class TestRAGSystemErrorPropagation:
    """Test that errors are properly propagated through the system"""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration"""
        config = Mock(spec=Config)
        config.CHUNK_SIZE = 800
        config.CHUNK_OVERLAP = 100
        config.MAX_RESULTS = 5
        config.CHROMA_PATH = "./test_chroma"
        config.EMBEDDING_MODEL = "all-MiniLM-L6-v2"
        config.ANTHROPIC_API_KEY = "test-key"
        config.ANTHROPIC_MODEL = "claude-3-sonnet"
        config.MAX_HISTORY = 2
        return config

    def test_vector_store_error_propagates(self, mock_config):
        """Test that vector store errors reach the query response"""
        with patch('rag_system.VectorStore') as mock_vs, \
             patch('rag_system.AIGenerator') as mock_ai, \
             patch('rag_system.SessionManager') as mock_sm, \
             patch('rag_system.DocumentProcessor'):

            # Setup vector store to return error
            from vector_store import SearchResults
            mock_vs_instance = MagicMock()
            mock_vs_instance.search.return_value = SearchResults(
                documents=[],
                metadata=[],
                distances=[],
                error="Database connection failed"
            )
            mock_vs.return_value = mock_vs_instance

            # Setup AI generator to NOT be called (tool should return error)
            mock_ai_instance = MagicMock()
            mock_ai.return_value = mock_ai_instance

            # Setup session manager
            mock_sm_instance = MagicMock()
            mock_sm.return_value = mock_sm_instance

            # Create RAG system
            rag = RAGSystem(mock_config)

            # Execute tool directly to see error
            result = rag.tool_manager.execute_tool(
                "search_course_content",
                query="test"
            )

            # Verify error message is returned
            assert result == "Database connection failed"

    def test_ai_generator_error_propagates(self, mock_config):
        """Test that AI generator errors are propagated"""
        with patch('rag_system.VectorStore'), \
             patch('rag_system.AIGenerator') as mock_ai, \
             patch('rag_system.SessionManager'), \
             patch('rag_system.DocumentProcessor'):

            # Setup AI generator to raise error
            mock_ai_instance = MagicMock()
            mock_ai_instance.generate_response.side_effect = Exception("API Error")
            mock_ai.return_value = mock_ai_instance

            # Create RAG system
            rag = RAGSystem(mock_config)

            # Query should raise the exception
            with pytest.raises(Exception) as exc_info:
                rag.query("test query")

            assert "API Error" in str(exc_info.value)
