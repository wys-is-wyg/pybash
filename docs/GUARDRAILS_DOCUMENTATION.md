# Guardrails and Prompt Injection Protection

## Overview

This document describes the guardrails and security measures in place to prevent prompt injection attacks when using AI models (sumy, llama-cpp-python, and Hugging Face transformers).

## Current Guardrails

### 1. Input Validation (`app/scripts/input_validator.py`)

**Purpose**: Validates and sanitizes all input before passing to AI models (sumy, llama-cpp-python, Hugging Face).

**Protection Against**:
- Prompt injection patterns (hex escapes, unicode escapes, script tags, etc.)
- Control characters
- Excessive special characters (potential obfuscation)
- Overly long inputs
- Suspicious patterns (SQL injection, template injection, etc.)

**Key Features**:
- **Injection Pattern Detection**: Detects 15+ suspicious patterns including:
  - Hex/Unicode escape sequences (`\x00`, `\u0000`)
  - Script tags (`<script>`, `javascript:`)
  - SQL keywords (`SELECT`, `INSERT`, etc.)
  - Template injection (`${...}`, `{{...}}`)
  - Dangerous function calls (`eval()`, `exec()`, `subprocess`)
  - Embedded content (`<iframe>`, `<embed>`)
  - Dangerous protocols (`vbscript:`, `data:text/html`)

- **Length Limits**: Maximum 8000 characters (~2000 tokens) per input
- **Control Character Removal**: Strips control characters except newlines/tabs
- **Special Character Ratio Check**: Flags inputs with >15% special characters
- **Repeated Pattern Detection**: Detects 3+ consecutive special characters

**Usage**:
```python
from app.scripts.input_validator import validate_for_summarization, validate_for_video_ideas

# For summarization (strict mode)
is_valid, sanitized_text, reason = validate_for_summarization(text)
if not is_valid:
    # Reject input
    return ""

# For video ideas (lenient mode - sanitizes but allows)
is_valid, sanitized_text, reason = validate_for_video_ideas(text)
```

### 2. HTML/Entity Cleaning (`app/scripts/summarizer.py`, `app/scripts/data_manager.py`)

**Purpose**: Removes HTML tags and decodes HTML entities before processing.

**Protection**:
- Removes all HTML tags (`<p>`, `<img>`, etc.)
- Decodes HTML entities (`&#8217;`, `&amp;`, etc.)
- Normalizes whitespace

**Usage**: Applied automatically in:
- `summarizer.py` - Before and after summarization
- `data_manager.py` - When merging feeds

### 3. Content Filtering (`app/scripts/filtering.py`, `app/scripts/pre_filter.py`)

**Purpose**: Filters articles for AI relevance and removes non-relevant content.

**Protection**:
- Topic relevance filtering (must match AI/ML topics)
- Negative keyword filtering (removes off-topic content)
- Deduplication (prevents duplicate processing)

### 4. Integration Points

#### Summarization Pipeline (`app/scripts/summarizer.py`)
1. Input validation via `validate_for_summarization()`
2. HTML/entity cleaning
3. **Primary**: Uses `sumy` library (TextRank algorithm) - fast extractive summarization, no model loading
4. **Fallback**: Hugging Face transformers (`facebook/bart-large-cnn`) - length limits enforced by pipeline
5. Output cleaning (HTML/entities removed from generated summary)

#### Video Idea Generation (`app/scripts/video_idea_generator.py`)
1. Input validation via `validate_for_video_ideas()` (lenient mode)
2. Topic extraction with validation
3. **Uses llama-cpp-python** with local LLM model (Llama 3.2 3B Instruct) for generation
4. Prompt-based generation with structured JSON output format
5. Model caching for performance (loaded once per worker process)

## Security Layers

### Layer 1: Input Validation (Pre-Processing)
- **Location**: `app/scripts/input_validator.py`
- **When**: Before any AI model call (sumy, llama-cpp-python, or Hugging Face)
- **Action**: Validates and sanitizes input, rejects suspicious content

### Layer 2: Content Cleaning (Pre-Processing)
- **Location**: `app/scripts/summarizer.py`, `app/scripts/data_manager.py`
- **When**: Before and after model processing
- **Action**: Removes HTML tags and entities

### Layer 3: Content Filtering (Pre-Processing)
- **Location**: `app/scripts/pre_filter.py`, `app/scripts/filtering.py`
- **When**: Before summarization
- **Action**: Filters for relevance, removes off-topic content

### Layer 4: Model Constraints (During Processing)
- **Location**: Model-specific configurations
- **When**: During model inference
- **Action**: 
  - **sumy**: Sentence count limits, stop word filtering
  - **llama-cpp-python**: max_tokens limits, stop sequences, temperature control
  - **Hugging Face**: max_length/min_length constraints, prevents excessive generation

## Current Architecture

### Summarization
- **Primary**: `sumy` library with TextRank algorithm
  - Fast extractive summarization (selects important sentences)
  - No model loading required
  - Lower injection risk (no prompt templates)
- **Fallback**: Hugging Face `facebook/bart-large-cnn` (if sumy unavailable)
  - Abstractive summarization (generates new text)
  - Requires model download (~1.6GB)

### Video Idea Generation
- **Uses**: `llama-cpp-python` with local LLM (Llama 3.2 3B Instruct)
  - Runs locally in Docker (no external API calls)
  - Structured prompt format with JSON output
  - Model cached per worker process for performance
  - Input validation and sanitization before prompt construction

## Security Benefits

1. **Local Processing**: All models run locally in Docker, reducing external attack surface
2. **Input Validation**: Comprehensive validation before any model processing
3. **No External APIs**: No reliance on external AI services (except optional Leonardo API for thumbnails)
4. **Model Caching**: Models loaded once per worker, reducing attack surface
5. **Structured Outputs**: JSON format validation for video ideas reduces injection risk

## Remaining Risks and Mitigations

### Risk 1: Malicious Content in RSS Feeds
**Mitigation**: 
- Input validation catches injection patterns
- Content filtering removes off-topic content
- HTML cleaning removes embedded scripts

### Risk 2: Overly Long Inputs
**Mitigation**: 
- Length limits enforced (8000 chars max)
- Truncation at word boundaries
- Model max_length constraints

### Risk 3: Obfuscated Injection Attempts
**Mitigation**:
- Special character ratio detection
- Repeated pattern detection
- Control character removal

### Risk 4: Model Output Manipulation
**Mitigation**:
- Output cleaning (HTML/entities removed)
- Length limits on generated content
- Validation of output structure

## Testing Guardrails

To test the guardrails, you can inject suspicious patterns into test data:

```python
# Test injection patterns
test_cases = [
    "<script>alert('xss')</script>",
    "${__import__('os').system('rm -rf /')}",
    "SELECT * FROM users",
    "javascript:alert('xss')",
    "\\x00\\x01\\x02",  # Control characters
    "{{7*7}}",  # Template injection
]

for test in test_cases:
    is_valid, sanitized, reason = validate_for_summarization(test)
    assert not is_valid, f"Should reject: {test}"
```

## Recommendations

1. **Monitor Logs**: Check for validation failures in logs
2. **Regular Updates**: Keep dependencies updated (sumy, llama-cpp-python, transformers)
3. **Rate Limiting**: ✅ **IMPLEMENTED** - Rate limiting added to all API endpoints
4. **Input Source Validation**: Validate RSS feed sources are trusted
5. **Output Validation**: Consider adding output validation for generated summaries
6. **Model Updates**: Keep LLM model files updated (download newer GGUF models if available)
7. **Cache Management**: Monitor cache usage via `/api/cache/stats` endpoint

## Files Modified

- `app/scripts/input_validator.py` (NEW) - Input validation module
- `app/scripts/summarizer.py` - Added input validation before summarization
- `app/scripts/video_idea_generator.py` - Added input validation before topic extraction

## Related Files

- `app/scripts/data_manager.py` - HTML cleaning in feed merging
- `app/scripts/filtering.py` - Content filtering and relevance scoring
- `app/scripts/pre_filter.py` - Pre-filtering for AI relevance

