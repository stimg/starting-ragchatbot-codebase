import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

@dataclass
class Config:
    """Configuration settings for the RAG system"""
    # Anthropic API settings
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"

    # Embedding model settings
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    # Document processing settings
    CHUNK_SIZE: int = 800       # Size of text chunks for vector storage
    CHUNK_OVERLAP: int = 100     # Characters to overlap between chunks
    MAX_RESULTS: int = 5         # Maximum search results to return (3-10 recommended for RAG)
    MAX_HISTORY: int = 2         # Number of conversation messages to remember

    # Database paths
    CHROMA_PATH: str = "./chroma_db"  # ChromaDB storage location

    def __post_init__(self):
        """Validate configuration values after initialization"""
        if self.MAX_RESULTS <= 0:
            raise ValueError(
                f"Configuration Error: MAX_RESULTS must be positive, got {self.MAX_RESULTS}. "
                f"Setting MAX_RESULTS to 0 will cause all searches to return empty results."
            )

        if not self.ANTHROPIC_API_KEY:
            raise ValueError(
                "Configuration Error: ANTHROPIC_API_KEY is required. "
                "Please set it in your .env file."
            )

        if self.CHUNK_SIZE <= 0:
            raise ValueError(
                f"Configuration Error: CHUNK_SIZE must be positive, got {self.CHUNK_SIZE}"
            )

        if self.CHUNK_OVERLAP < 0 or self.CHUNK_OVERLAP >= self.CHUNK_SIZE:
            raise ValueError(
                f"Configuration Error: CHUNK_OVERLAP must be between 0 and CHUNK_SIZE. "
                f"Got CHUNK_OVERLAP={self.CHUNK_OVERLAP}, CHUNK_SIZE={self.CHUNK_SIZE}"
            )

config = Config()


