# Proposed Fixes for RAG Chatbot "Query Failed" Issue

## Summary

The RAG chatbot returns "query failed" for content-related questions due to `MAX_RESULTS = 0` in the configuration, causing all vector searches to return empty results.

## Primary Fix (REQUIRED)

### Fix #1: Update MAX_RESULTS Configuration

**Priority**: 🔴 CRITICAL - Blocks all content queries

**File**: `backend/config.py`
**Line**: 21

#### Current Code:
```python
MAX_RESULTS: int = 0         # Maximum search results to return
```

#### Fixed Code:
```python
MAX_RESULTS: int = 5         # Maximum search results to return
```

#### Explanation:
- Setting MAX_RESULTS to 0 causes ChromaDB to return 0 documents
- This makes all searches return "No relevant content found"
- 5 is a reasonable default for RAG systems (provides enough context without overwhelming the AI)
- Matches the default parameter in `VectorStore.__init__(max_results=5)`

#### Testing:
```bash
# After making the change, restart the server and test:
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is prompt caching?"}'

# Should return actual course content, not "No relevant content found"
```

---

## Secondary Fixes (RECOMMENDED)

### Fix #2: Add Configuration Validation

**Priority**: 🟡 HIGH - Prevents similar issues in future

**File**: `backend/config.py`
**Location**: After the Config class definition

#### Add:
```python
@dataclass
class Config:
    """Configuration settings for the RAG system"""
    # ... existing fields ...

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
            raise ValueError(f"Configuration Error: CHUNK_SIZE must be positive, got {self.CHUNK_SIZE}")

        if self.CHUNK_OVERLAP < 0 or self.CHUNK_OVERLAP >= self.CHUNK_SIZE:
            raise ValueError(
                f"Configuration Error: CHUNK_OVERLAP must be between 0 and CHUNK_SIZE. "
                f"Got CHUNK_OVERLAP={self.CHUNK_OVERLAP}, CHUNK_SIZE={self.CHUNK_SIZE}"
            )


# Validate configuration at module load time
config = Config()
```

#### Benefits:
- Fails fast at startup with clear error messages
- Prevents silent failures during runtime
- Helps developers catch configuration issues immediately
- Makes debugging much easier

---

### Fix #3: Add Runtime Validation in VectorStore

**Priority**: 🟡 MEDIUM - Defense in depth

**File**: `backend/vector_store.py`
**Line**: 37 (in `__init__` method)

#### Current Code:
```python
def __init__(self, chroma_path: str, embedding_model: str, max_results: int = 5):
    self.max_results = max_results
    # ... rest of initialization
```

#### Fixed Code:
```python
def __init__(self, chroma_path: str, embedding_model: str, max_results: int = 5):
    if max_results <= 0:
        raise ValueError(
            f"max_results must be positive, got {max_results}. "
            f"A value of 0 will cause all searches to return empty results."
        )

    self.max_results = max_results
    # ... rest of initialization
```

#### Benefits:
- Validates input at the component level
- Provides clear error message if misconfigured
- Follows defensive programming practices

---

## Verification Steps

### 1. Run Test Suite
```bash
cd backend
uv run pytest tests/ -v
```

**Expected**: All 46 tests pass (currently 44 pass, 2 fail due to the bug)

### 2. Manual Testing

#### Start the server:
```bash
./run.sh
```

#### Test content query:
```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is prompt caching?",
    "session_id": "test123"
  }'
```

**Expected Response**:
```json
{
  "answer": "Prompt caching is a feature that retains some of the results...",
  "sources": [
    {
      "text": "Building Towards Computer Use with Anthropic - Lesson 0",
      "link": "https://learn.deeplearning.ai/courses/..."
    }
  ],
  "session_id": "test123"
}
```

**NOT Expected**: `"answer": "No relevant content found"`

#### Test course outline query:
```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What lessons are in the Computer Use course?"}'
```

**Expected**: Should return course outline with lesson list

### 3. Browser Testing

1. Open http://localhost:8000
2. Ask: "What is prompt caching?"
3. **Expected**: Get detailed answer with sources
4. **NOT Expected**: "No relevant content found" or query failure

---

## Implementation Order

1. ✅ **Apply Fix #1** (MAX_RESULTS = 5) - REQUIRED
2. ✅ **Apply Fix #2** (Config validation) - RECOMMENDED
3. ✅ **Apply Fix #3** (VectorStore validation) - OPTIONAL but good practice
4. ✅ **Run tests** to verify all pass
5. ✅ **Manual testing** to confirm functionality
6. ✅ **Deploy** to production

---

## Additional Recommendations

### Short-term (Before Next Deployment)

1. **Document Configuration**: Add comments explaining each config value
   ```python
   MAX_RESULTS: int = 5  # Number of document chunks to retrieve for each query
                         # Higher = more context but slower; Lower = faster but less context
                         # Recommended range: 3-10
   ```

2. **Add .env.example**: Include example with proper values
   ```env
   ANTHROPIC_API_KEY=your-api-key-here
   # MAX_RESULTS defaults to 5, but can be overridden if needed
   ```

### Medium-term (Future Improvements)

1. **Add Integration Tests**: Test actual document loading and querying
2. **Add Monitoring**: Log when searches return empty results
3. **Add Metrics**: Track search result counts and quality
4. **Consider Dynamic Limits**: Adjust MAX_RESULTS based on query complexity

---

## Impact Assessment

### Before Fix:
- ❌ All content queries fail
- ❌ Search tool returns "No relevant content found"
- ❌ Users cannot get answers about course materials
- ❌ Only general knowledge questions work

### After Fix:
- ✅ Content queries return relevant information
- ✅ Search tool finds matching course content
- ✅ Users get accurate answers with source citations
- ✅ Full chatbot functionality restored

---

## Questions?

If you encounter issues after applying these fixes:

1. Check that documents were loaded at startup:
   ```
   # Server logs should show:
   Loading initial documents...
   Loaded 4 courses with N chunks
   ```

2. Verify ChromaDB has data:
   ```bash
   ls -la backend/chroma_db/
   # Should see database files
   ```

3. Check API key is set:
   ```bash
   # In backend/.env
   ANTHROPIC_API_KEY=sk-ant-api03-...
   ```

4. Run tests to verify functionality:
   ```bash
   cd backend && uv run pytest tests/test_vector_store.py -v
   ```
