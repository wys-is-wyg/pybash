# Vote System Implementation Tasks

## Overview

Create a voting system for design variants (kiwilab1-6) with a dedicated page that displays previews in a modal, allows voting, and shows voting statistics in a bar graph.

## Tasks

### 1. Frontend Implementation

- [ ] Create `vote.html` with similar styling to main app but using yellow instead of orange
  - [ ] Header with logo/branding
  - [ ] Design variant cards/thumbnails (kiwilab1-6)
  - [ ] Modal popup for viewing full design previews
  - [ ] Vote button for each design
  - [ ] Bar graph displaying vote distribution at top
  - [ ] Display current voting status (optional: show user's vote)
  - [ ] Responsive design for mobile/tablet

### 2. Backend Routes & Logic

- [ ] Create Flask route for `/vote` endpoint serving vote.html
- [ ] Create API endpoint `/api/vote` (POST) to record votes
  - [ ] Accept design variant ID
  - [ ] Track votes in persistent storage (JSON or database)
  - [ ] Return success response
- [ ] Create API endpoint `/api/vote-stats` (GET) to retrieve voting data
  - [ ] Return vote counts for each variant
  - [ ] Format for bar graph display

### 3. Data Persistence

- [ ] Create/configure votes storage location (e.g., `app/data/votes.json`)
- [ ] Implement vote tracking logic in Python backend
  - [ ] Initialize file if doesn't exist
  - [ ] Increment vote counts
  - [ ] Persist to disk

### 4. Frontend JavaScript

- [ ] Implement modal functionality for design previews
- [ ] Implement vote submission with fetch API
- [ ] Implement bar graph rendering (Chart.js or similar)
- [ ] Load and display initial voting statistics
- [ ] Handle user interactions (prevent double voting, etc.)

### 5. Styling & Design

- [ ] Apply yellow color scheme instead of orange
- [ ] Match main app's design system
- [ ] Ensure visual consistency across pages
- [ ] Add appropriate transitions/animations

### 6. Testing & Deployment

- [ ] Test voting functionality locally
- [ ] Verify data persistence
- [ ] Test modal interactions
- [ ] Test bar graph updates
- [ ] Ensure route is not exposed in main nav
- [ ] Test Docker deployment

## Notes

- Vote page should NOT be linked in main app navigation
- Leverage existing Python/Docker infrastructure
- Kiwilab HTML files already exist at `/web/public/kiwilabs/kiwilab{1-6}/`
- Yellow color scheme should complement existing design language
