# Guardrails and Prompt Injection Protection

## Overview

This document describes the guardrails and security measures in place to prevent prompt injection attacks when using Hugging Face models.

## Current Guardrails

### 1. Input Validation (`app/scripts/input_validator.py`)

**Purpose**: Validates and sanitizes all input before passing to Hugging Face models.

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
3. Length limits enforced by Hugging Face pipeline
4. Output cleaning (HTML/entities removed from generated summary)

#### Video Idea Generation (`app/scripts/video_idea_generator.py`)
1. Input validation via `validate_for_video_ideas()` (lenient mode)
2. Topic extraction with validation
3. Template-based generation (no direct model calls, lower risk)

## Security Layers

### Layer 1: Input Validation (Pre-Processing)
- **Location**: `app/scripts/input_validator.py`
- **When**: Before any Hugging Face model call
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
- **Location**: Hugging Face pipeline configuration
- **When**: During model inference
- **Action**: Enforces max_length/min_length, prevents excessive generation

## Why Hugging Face is Safer

1. **No Prompt Templates**: Hugging Face models receive raw text, not formatted prompts with system instructions. This reduces injection risk.

2. **Deterministic Processing**: The summarization pipeline uses `do_sample=False`, making output more predictable.

3. **Template-Based Video Ideas**: Video idea generation uses template-based keyword extraction, not direct model calls.

4. **Local Processing**: Models run locally in Docker, reducing external attack surface.

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
2. **Regular Updates**: Keep Hugging Face transformers library updated
3. **Rate Limiting**: Consider rate limiting on API endpoints
4. **Input Source Validation**: Validate RSS feed sources are trusted
5. **Output Validation**: Consider adding output validation for generated summaries

## Files Modified

- `app/scripts/input_validator.py` (NEW) - Input validation module
- `app/scripts/summarizer.py` - Added input validation before summarization
- `app/scripts/video_idea_generator.py` - Added input validation before topic extraction

## Related Files

- `app/scripts/data_manager.py` - HTML cleaning in feed merging
- `app/scripts/filtering.py` - Content filtering and relevance scoring
- `app/scripts/pre_filter.py` - Pre-filtering for AI relevance

