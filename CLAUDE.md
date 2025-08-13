# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Application

### Setup & Run
```bash
# First time setup
uv sync
cp .env.example .env

# For local Ollama (default - no API key needed):
ollama pull qwen2.5:7b

# For Anthropic Claude (alternative):
Edit .env: set AI_PROVIDER=anthropic and add ANTHROPIC_API_KEY

# Run application
./run.sh
```

### Access Points
- Web Interface: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## Architecture Overview

This is a **RAG (Retrieval-Augmented Generation) system** that provides intelligent answers about course materials through a web interface.

### Core Architecture Pattern: Tool-Based RAG

Unlike traditional RAG systems that always retrieve documents, this system uses **AI-driven tool selection**:

1. **AI First Approach**: Claude AI determines if a search is needed based on the query
2. **Tool-Based Search**: Only searches course content when the AI requests it via tools
3. **Smart Filtering**: Search tool can filter by course name and lesson number semantically
4. **Source Tracking**: Maintains provenance of information for user transparency

### Component Relationships

```
Frontend (Vanilla JS) → FastAPI → RAG System → AI Generator ↔ Search Tools → Vector Store
                                     ↕                                            ↕
                                Session Manager                              ChromaDB + Embeddings
```

### Key Components

**RAG System (`rag_system.py`)**: Central orchestrator that coordinates all components. Manages the query lifecycle from user input to final response.

**AI Generator (`ai_generator.py`)**: Handles Claude API interactions with tool calling. Uses a static system prompt optimized for educational content and manages conversation flow with tool execution.

**Search Tools (`search_tools.py`)**: Implements the `CourseSearchTool` that provides semantic search with intelligent course name matching. Uses a plugin architecture for extensibility.

**Vector Store (`vector_store.py`)**: ChromaDB wrapper with dual collections - one for course metadata and one for content chunks. Provides unified search interface with course/lesson filtering.

**Document Processor (`document_processor.py`)**: Extracts structured course information from text files and creates overlapping chunks optimized for semantic search.

**Session Manager (`session_manager.py`)**: Maintains conversation history with configurable retention limits for context persistence.

### Data Models (`models.py`)

- **Course**: Complete course structure with lessons
- **Lesson**: Individual lesson with optional links
- **CourseChunk**: Text chunks with course/lesson metadata for vector storage

### Configuration (`config.py` + `model_config.json`)

Centralized configuration using environment variables and external model configuration:
- **AI Provider**: Choose between "ollama" (default, local) or "anthropic" (cloud)
- **Model Configuration**: Managed via `backend/model_config.json` for easy model switching
- **Ollama settings**: Default model (qwen2.5:7b) with available alternatives, base URL
- **Anthropic API settings**: API key and model selection
- **Streaming Support**: Real-time response display for better user experience
- Embedding model (all-MiniLM-L6-v2)
- Chunk processing parameters
- ChromaDB storage location

### Frontend Architecture

**Single Page Application** using vanilla JavaScript:
- **Event-driven**: User interactions trigger HTTP requests to backend API
- **Asynchronous UI**: Loading states and error handling for better UX
- **Source Display**: Collapsible sections showing information provenance
- **Session Persistence**: Maintains conversation context across page refreshes

### Document Processing Pipeline

1. **File Reading**: Supports .txt, .pdf, .docx with UTF-8 encoding
2. **Structure Extraction**: Parses course titles, lessons, and content using regex patterns
3. **Chunking**: Sentence-aware chunking with configurable overlap (800 chars, 100 overlap)
4. **Dual Storage**: Course metadata and content chunks stored separately for optimized search

### Search Strategy

**Semantic Search with Metadata Filtering**:
- Course name matching uses similarity search for partial matches
- Lesson filtering by exact number match
- Results formatted with contextual headers
- Source tracking for UI display

### API Design

**RESTful endpoints**:
- `POST /api/query`: Main query processing with session management
- `GET /api/courses`: Course statistics and metadata
- FastAPI with automatic OpenAPI documentation

### Error Handling Patterns

- **Graceful Degradation**: Failed document processing doesn't stop the system
- **Error Propagation**: Clear error messages from AI tool execution
- **Fallback Responses**: System continues without search if vector store fails

### Development Notes

- **No Test Framework**: Currently no automated testing infrastructure
- **AI Provider Options**: 
  - Default: Local Ollama with qwen2.5:7b (no API key needed, faster responses)
  - Alternative: Anthropic Claude (requires API key)
- **Local Setup**: Requires Ollama installation and model download (`ollama pull qwen2.5:7b`)
- **Model Switching**: Edit `backend/model_config.json` to change between qwen2.5:7b, qwen3:8b, qwen3:14b, etc.
- **Data Persistence**: ChromaDB stores data in `backend/chroma_db/` directory
- **Document Loading**: Course documents automatically loaded from `docs/` on startup
- always use uv to run the server do not use pip directly
- when updating CSS style, remember to update the version as well to avoid cached browser