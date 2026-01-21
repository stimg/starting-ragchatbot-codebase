# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A RAG (Retrieval-Augmented Generation) chatbot that answers questions about course materials using semantic search (ChromaDB) and Claude AI.

## Development Commands

**Always use `uv` for all dependency management and running Python—never use `pip` or `python` directly.**
- Install deps: `uv sync`
- Add a package: `uv add <package>`
- Run Python files: `uv run python <file.py>`
- Run commands: `uv run <command>`

```bash
# Install dependencies
uv sync

# Run the server (from project root)
./run.sh
# Or manually:
cd backend && uv run uvicorn app:app --reload --port 8000

# Access points
# Web UI: http://localhost:8000
# API docs: http://localhost:8000/docs
```

## Architecture

### Data Flow
1. Documents in `/docs/*.txt` are parsed and chunked at startup
2. Chunks are embedded using `all-MiniLM-L6-v2` and stored in ChromaDB
3. User queries hit `/api/query` → RAG system → Claude with search tools
4. Claude can call `search_course_content` tool to retrieve relevant chunks
5. Response is generated using retrieved context

### Backend Components (`backend/`)
- **app.py**: FastAPI server, mounts frontend, defines `/api/query` and `/api/courses` endpoints
- **rag_system.py**: Orchestrator that wires together all components, handles document loading and query processing
- **vector_store.py**: ChromaDB wrapper with two collections: `course_catalog` (metadata) and `course_content` (chunks). Handles semantic search with course/lesson filtering
- **ai_generator.py**: Claude API integration with tool execution loop
- **document_processor.py**: Parses course files (extracts title, instructor, lessons), chunks text with 800 char size / 100 char overlap
- **session_manager.py**: Manages conversation history per session (max 2 turns)
- **search_tools.py**: Defines `CourseSearchTool` for Claude's tool use

### Frontend (`frontend/`)
Vanilla HTML/CSS/JS chat interface. `script.js` handles API calls and session management.

### Key Configuration (`config.py`)
- Embedding model: `all-MiniLM-L6-v2`
- Claude model: `claude-sonnet-4-20250514`
- Chunk size: 800 chars, overlap: 100 chars
- Docs path: `../docs`

## Environment Setup

Requires `.env` file with:
```
ANTHROPIC_API_KEY=your_key_here
```