# Pipeline Refactoring Plan

## Goal
Simplify the data pipeline by removing redundant data duplication and complex merging logic. Each stage outputs minimal, clean data that can be easily merged by article ID.

## Architecture

### File Structure
```
raw_news.json          → All scraped articles (never modified, preserve original)
filtered_news.json     → Filtered articles (minimal: article_id, title, source_url, published_date, source)
summaries.json         → Just summaries with article_id reference
video_ideas.json       → Just video ideas with article_id, LLM title, LLM description
display.json           → Lightweight merge for frontend (all data merged by article_id)
```

### Data Flow
1. **Scrape** → `raw_news.json` (preserve original, never overwrite)
2. **Filter** → `filtered_news.json` (minimal fields, add `article_id` hash)
3. **Summarize** → `summaries.json` (article_id + summary only)
4. **Generate Ideas** → `video_ideas.json` (article_id + LLM title + LLM description only)
5. **Build Display** → `display.json` (merge all by article_id for frontend)

### Article ID
- Use hash of `source_url` for consistent article identification
- Format: `hashlib.md5(source_url.encode()).hexdigest()[:16]` (16-char hex)

---

## Phase 1: Data Structure Changes

### 1.1 Add Article ID Generation
- [ ] Create `article_id` utility function in `data_manager.py` or new `utils.py`
- [ ] Function: `generate_article_id(source_url: str) -> str`
- [ ] Use MD5 hash of source_url, take first 16 chars

### 1.2 Update Settings
- [ ] Add `FILTERED_NEWS_FILE` constant to `settings.py`
- [ ] Update file path constants if needed

### 1.3 Update Pre-Filter
- [ ] Modify `pre_filter.py` to save to `filtered_news.json` (don't overwrite `raw_news.json`)
- [ ] Add `article_id` to each filtered article
- [ ] Keep minimal fields: `article_id`, `title`, `source_url`, `published_date`, `source`, `author` (if available)

### 1.4 Update Summarizer
- [ ] Modify `summarizer.py` to output minimal format: `{article_id, summary}`
- [ ] Read from `filtered_news.json` instead of `raw_news.json`
- [ ] Output format: `{"items": [{"article_id": "...", "summary": "..."}]}`

### 1.5 Update Video Idea Generator
- [ ] Modify `video_idea_generator.py` to output clean format
- [ ] Extract actual LLM title and description (from JSON in description field)
- [ ] Output format: `{"items": [{"article_id": "...", "video_title": "...", "video_description": "..."}]}`
- [ ] Remove all redundant fields (no original_title, original_summary, etc.)
- [ ] Use LLM's actual title and description, not structured fields

---

## Phase 2: Data Manager Refactor

### 2.1 Simplify Merge Logic
- [ ] Rewrite `merge_feeds()` to lightweight merge by `article_id`
- [ ] Load: `filtered_news.json`, `summaries.json`, `video_ideas.json`
- [ ] Create lookup dictionaries by `article_id`
- [ ] Merge into single structure

### 2.2 Create Display Builder
- [ ] Create `build_display_data()` function
- [ ] Merge all data sources by `article_id`
- [ ] Output format optimized for frontend
- [ ] Include: article data, summary, video_ideas array (if exists)

### 2.3 Update Feed Generation
- [ ] Update `generate_feed_json()` to use new structure
- [ ] Remove complex JSON parsing logic
- [ ] Use clean data from video_ideas.json

### 2.4 Remove Old Logic
- [ ] Remove malformed JSON parsing from video ideas
- [ ] Remove redundant field copying
- [ ] Simplify code paths

---

## Phase 3: Pipeline Updates

### 3.1 Update Pipeline Script
- [ ] Update `run_pipeline.sh` to use new file names
- [ ] Update cleanup function to preserve `raw_news.json`
- [ ] Update file references throughout script
- [ ] Update step descriptions

### 3.2 Update Pipeline Endpoint
- [ ] Rewrite file creation in Flask endpoint (`/api/refresh` or pipeline trigger)
- [ ] Use new `build_display_data()` function
- [ ] Update error handling for new file structure

---

## Phase 4: Frontend Updates

### 4.1 Update Feed Loading
- [ ] Update `app.js` to load `display.json` (or merge on-the-fly)
- [ ] Update feed rendering to use new structure
- [ ] Test with new data format

### 4.2 Update Video Ideas Section
- [ ] Update video ideas rendering to use new structure
- [ ] Ensure article title and link display correctly
- [ ] Test video ideas display

### 4.3 Remove Old Dependencies
- [ ] Remove any code that expects old `feed.json` structure
- [ ] Update any hardcoded field references

---

## Phase 5: Testing & Cleanup

### 5.1 Testing
- [ ] Test each pipeline stage independently
- [ ] Verify article_id consistency across stages
- [ ] Test frontend with new data structure
- [ ] Verify video ideas display correctly

### 5.2 Cleanup
- [ ] Remove old merging logic
- [ ] Remove unused functions
- [ ] Update documentation
- [ ] Clean up any temporary code

---

## Implementation Notes

### Article ID Format
```python
import hashlib

def generate_article_id(source_url: str) -> str:
    """Generate consistent article ID from source URL."""
    return hashlib.md5(source_url.encode()).hexdigest()[:16]
```

### Video Ideas Format (from LLM)
```json
{
  "items": [
    {
      "article_id": "a1b2c3d4e5f6g7h8",
      "video_title": "From Code to Reality: How AI Can Revolutionize Your Next Project",
      "video_description": "In this video, we'll explore how AI and machine learning..."
    }
  ]
}
```

### Display.json Format
```json
{
  "version": "2.0",
  "generated_at": "2025-12-08T...",
  "items": [
    {
      "article_id": "a1b2c3d4e5f6g7h8",
      "type": "news",
      "title": "Article Title",
      "summary": "Article summary...",
      "source_url": "https://...",
      "published_date": "2025-12-08T...",
      "source": "Source Name",
      "video_ideas": [
        {
          "video_title": "Video Idea Title",
          "video_description": "Video idea description..."
        }
      ]
    }
  ]
}
```

---

## Migration Strategy

1. **Backward Compatibility**: None - clean break, ignore old files
2. **Testing**: Run full pipeline after each phase
3. **Rollback**: Git commit after each phase for easy rollback
4. **Documentation**: Update as we go

---

## Status

- [ ] Phase 1: Data Structure Changes
- [ ] Phase 2: Data Manager Refactor
- [ ] Phase 3: Pipeline Updates
- [ ] Phase 4: Frontend Updates
- [ ] Phase 5: Testing & Cleanup

