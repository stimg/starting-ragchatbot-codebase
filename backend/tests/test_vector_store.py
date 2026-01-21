"""Tests for vector store search functionality"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from vector_store import VectorStore, SearchResults
from models import Course, Lesson, CourseChunk


class TestSearchResults:
    """Test SearchResults dataclass"""

    def test_from_chroma_with_results(self):
        """Test creating SearchResults from ChromaDB response"""
        chroma_results = {
            'documents': [['doc1', 'doc2']],
            'metadatas': [[{'key': 'value1'}, {'key': 'value2'}]],
            'distances': [[0.1, 0.2]]
        }

        results = SearchResults.from_chroma(chroma_results)

        assert results.documents == ['doc1', 'doc2']
        assert results.metadata == [{'key': 'value1'}, {'key': 'value2'}]
        assert results.distances == [0.1, 0.2]
        assert results.error is None

    def test_from_chroma_with_empty_results(self):
        """Test creating SearchResults from empty ChromaDB response"""
        chroma_results = {
            'documents': [[]],
            'metadatas': [[]],
            'distances': [[]]
        }

        results = SearchResults.from_chroma(chroma_results)

        assert results.is_empty()
        assert results.documents == []
        assert results.metadata == []

    def test_empty_constructor(self):
        """Test creating empty SearchResults with error"""
        results = SearchResults.empty("Test error message")

        assert results.is_empty()
        assert results.error == "Test error message"

    def test_is_empty(self):
        """Test is_empty method"""
        empty_results = SearchResults([], [], [], None)
        assert empty_results.is_empty()

        non_empty_results = SearchResults(['doc'], [{}], [0.1], None)
        assert not non_empty_results.is_empty()


class TestVectorStoreSearch:
    """Test VectorStore search functionality"""

    @pytest.fixture
    def mock_chroma_client(self):
        """Create a mock ChromaDB client"""
        mock_client = MagicMock()

        # Mock collection
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            'documents': [['Test content']],
            'metadatas': [[{'course_title': 'Test', 'lesson_number': 1}]],
            'distances': [[0.1]]
        }

        mock_client.get_or_create_collection.return_value = mock_collection

        return mock_client

    def test_search_basic_query(self, tmp_path):
        """Test basic search without filters"""
        with patch('chromadb.PersistentClient') as mock_client_class:
            mock_collection = MagicMock()
            mock_collection.query.return_value = {
                'documents': [['Test document']],
                'metadatas': [[{'course_title': 'Test', 'lesson_number': 1}]],
                'distances': [[0.1]]
            }

            mock_client = MagicMock()
            mock_client.get_or_create_collection.return_value = mock_collection
            mock_client_class.return_value = mock_client

            store = VectorStore(
                chroma_path=str(tmp_path),
                embedding_model="all-MiniLM-L6-v2",
                max_results=5
            )

            results = store.search(query="test query")

            # Verify query was called
            mock_collection.query.assert_called_once_with(
                query_texts=["test query"],
                n_results=5,
                where=None
            )

            assert not results.is_empty()
            assert results.documents == ['Test document']

    def test_search_with_course_name_filter(self, tmp_path):
        """Test search with course name resolution"""
        with patch('chromadb.PersistentClient') as mock_client_class:
            # Mock catalog collection (for course name resolution)
            mock_catalog = MagicMock()
            mock_catalog.query.return_value = {
                'documents': [['Test Course']],
                'metadatas': [[{'title': 'Full Test Course Name'}]],
                'distances': [[0.0]]
            }

            # Mock content collection (for actual search)
            mock_content = MagicMock()
            mock_content.query.return_value = {
                'documents': [['Course content']],
                'metadatas': [[{'course_title': 'Full Test Course Name', 'lesson_number': 1}]],
                'distances': [[0.1]]
            }

            mock_client = MagicMock()

            def get_collection(name, **kwargs):
                if name == "course_catalog":
                    return mock_catalog
                elif name == "course_content":
                    return mock_content

            mock_client.get_or_create_collection.side_effect = get_collection
            mock_client_class.return_value = mock_client

            store = VectorStore(
                chroma_path=str(tmp_path),
                embedding_model="all-MiniLM-L6-v2",
                max_results=5
            )

            results = store.search(
                query="test query",
                course_name="Test"
            )

            # Verify catalog was queried for course name
            mock_catalog.query.assert_called_once()

            # Verify content was searched with filter
            mock_content.query.assert_called_once_with(
                query_texts=["test query"],
                n_results=5,
                where={'course_title': 'Full Test Course Name'}
            )

    def test_search_with_lesson_number_filter(self, tmp_path):
        """Test search with lesson number filter"""
        with patch('chromadb.PersistentClient') as mock_client_class:
            mock_collection = MagicMock()
            mock_collection.query.return_value = {
                'documents': [['Lesson content']],
                'metadatas': [[{'course_title': 'Test', 'lesson_number': 3}]],
                'distances': [[0.1]]
            }

            mock_client = MagicMock()
            mock_client.get_or_create_collection.return_value = mock_collection
            mock_client_class.return_value = mock_client

            store = VectorStore(
                chroma_path=str(tmp_path),
                embedding_model="all-MiniLM-L6-v2",
                max_results=5
            )

            results = store.search(
                query="test query",
                lesson_number=3
            )

            # Verify lesson filter was applied
            mock_collection.query.assert_called_once_with(
                query_texts=["test query"],
                n_results=5,
                where={'lesson_number': 3}
            )

    def test_search_with_both_filters(self, tmp_path):
        """Test search with both course and lesson filters"""
        with patch('chromadb.PersistentClient') as mock_client_class:
            # Mock catalog
            mock_catalog = MagicMock()
            mock_catalog.query.return_value = {
                'documents': [['Test Course']],
                'metadatas': [[{'title': 'Resolved Course'}]],
                'distances': [[0.0]]
            }

            # Mock content
            mock_content = MagicMock()
            mock_content.query.return_value = {
                'documents': [['Content']],
                'metadatas': [[{'course_title': 'Resolved Course', 'lesson_number': 2}]],
                'distances': [[0.1]]
            }

            mock_client = MagicMock()

            def get_collection(name, **kwargs):
                if name == "course_catalog":
                    return mock_catalog
                return mock_content

            mock_client.get_or_create_collection.side_effect = get_collection
            mock_client_class.return_value = mock_client

            store = VectorStore(
                chroma_path=str(tmp_path),
                embedding_model="all-MiniLM-L6-v2",
                max_results=5
            )

            results = store.search(
                query="test",
                course_name="Test",
                lesson_number=2
            )

            # Verify combined filter was applied
            expected_filter = {
                '$and': [
                    {'course_title': 'Resolved Course'},
                    {'lesson_number': 2}
                ]
            }
            mock_content.query.assert_called_once_with(
                query_texts=["test"],
                n_results=5,
                where=expected_filter
            )

    def test_vector_store_rejects_zero_max_results(self, tmp_path):
        """Test that VectorStore validates and rejects max_results=0"""
        import pytest

        # Attempting to create VectorStore with max_results=0 should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            store = VectorStore(
                chroma_path=str(tmp_path),
                embedding_model="all-MiniLM-L6-v2",
                max_results=0
            )

        # Verify helpful error message
        assert "max_results must be positive" in str(exc_info.value)
        assert "0" in str(exc_info.value)

    def test_search_with_custom_limit(self, tmp_path):
        """Test that custom limit overrides max_results"""
        with patch('chromadb.PersistentClient') as mock_client_class:
            mock_collection = MagicMock()
            mock_collection.query.return_value = {
                'documents': [['doc']],
                'metadatas': [[{}]],
                'distances': [[0.1]]
            }

            mock_client = MagicMock()
            mock_client.get_or_create_collection.return_value = mock_collection
            mock_client_class.return_value = mock_client

            store = VectorStore(
                chroma_path=str(tmp_path),
                embedding_model="all-MiniLM-L6-v2",
                max_results=5
            )

            # Search with custom limit
            results = store.search(query="test", limit=10)

            # Verify custom limit was used
            mock_collection.query.assert_called_once_with(
                query_texts=["test"],
                n_results=10,  # Custom limit should override
                where=None
            )

    def test_search_handles_chroma_exception(self, tmp_path):
        """Test that ChromaDB exceptions are caught and returned as errors"""
        with patch('chromadb.PersistentClient') as mock_client_class:
            mock_collection = MagicMock()
            mock_collection.query.side_effect = Exception("ChromaDB error")

            mock_client = MagicMock()
            mock_client.get_or_create_collection.return_value = mock_collection
            mock_client_class.return_value = mock_client

            store = VectorStore(
                chroma_path=str(tmp_path),
                embedding_model="all-MiniLM-L6-v2",
                max_results=5
            )

            results = store.search(query="test")

            # Should return error result
            assert results.error is not None
            assert "ChromaDB error" in results.error

    def test_resolve_course_name_returns_none_for_no_match(self, tmp_path):
        """Test that _resolve_course_name returns None when no course found"""
        with patch('chromadb.PersistentClient') as mock_client_class:
            mock_catalog = MagicMock()
            mock_catalog.query.return_value = {
                'documents': [[]],  # No results
                'metadatas': [[]],
                'distances': [[]]
            }

            mock_client = MagicMock()
            mock_client.get_or_create_collection.return_value = mock_catalog
            mock_client_class.return_value = mock_client

            store = VectorStore(
                chroma_path=str(tmp_path),
                embedding_model="all-MiniLM-L6-v2",
                max_results=5
            )

            # Try to search with non-existent course
            results = store.search(query="test", course_name="Nonexistent")

            # Should return error about course not found
            assert results.error is not None
            assert "No course found" in results.error
