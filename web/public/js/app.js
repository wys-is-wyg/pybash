/**
 * AI News Tracker - Frontend Application
 * Handles feed fetching, rendering, navigation, and auto-refresh
 */

// API base URL - use relative path since server.js proxies /api to python-app
const API_BASE_URL = "/api";

// Auto-refresh interval (5 minutes = 300000ms)
const REFRESH_INTERVAL = 300000;

// State management
let currentFeedData = [];
let refreshTimer = null;
let currentFeedTag = "all";
let currentFeedSource = "all";
let currentVideoIdeasTag = "all";
let currentVideoIdeasSource = "all";

/**
 * Fetches feed data from the API
 * @returns {Promise<Array>} Array of feed items
 */
async function fetchFeed() {
  try {
    const response = await fetch(`${API_BASE_URL}/news`);

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return Array.isArray(data) ? data : [];
  } catch (error) {
    console.error("Error fetching feed:", error);
    throw error;
  }
}

/**
 * Renders feed items into the feed container
 * @param {Array} feedData - Array of feed items with title, summary, thumbnail, source
 */
function renderFeed(feedData) {
  const container = document.getElementById("feed-container");
  const errorContainer = document.getElementById("feed-error");
  const emptyContainer = document.getElementById("feed-empty");

  // Hide error and empty states initially
  if (errorContainer) errorContainer.style.display = "none";
  if (emptyContainer) emptyContainer.style.display = "none";

  // Clear container
  if (!container) return;
  container.innerHTML = "";

  // Handle empty feed
  if (!feedData || feedData.length === 0) {
    if (emptyContainer) emptyContainer.style.display = "block";
    updateFeedStatus("empty", "No items available");
    return;
  }

  // Update status
  updateFeedStatus("success", "Loaded");
  updateFeedTimestamp();

  // Update tag filter buttons (use all data to show all available tags)
  updateTagFilters(feedData, "feed-tag-filters");
  updateSourceFilters(feedData, "feed-source-filters");

  // Filter by tag if not "all"
  let filteredData = feedData;
  if (currentFeedTag !== "all") {
    filteredData = filteredData.filter((item) => {
      const tags = item.visual_tags || [];
      return tags.includes(currentFeedTag);
    });
  }

  // Filter by source if not "all"
  if (currentFeedSource !== "all") {
    filteredData = filteredData.filter((item) => {
      const source = item.source || "";
      return source.toLowerCase() === currentFeedSource.toLowerCase();
    });
  }

  // Render each feed item as a card
  filteredData.forEach((item) => {
    const card = createFeedCard(item);
    container.appendChild(card);
  });
}

/**
 * Creates a feed card element from an item
 * @param {Object} item - Feed item with title, summary, thumbnail_url, source_url, etc.
 * @returns {HTMLElement} Card element
 */
function createFeedCard(item) {
  const card = document.createElement("div");
  card.className = "news-card";

  // Thumbnail - use news-card-image class to match CSS
  const thumbnail = document.createElement("div");
  thumbnail.className = "news-card-image";
  if (item.thumbnail_url) {
    const img = document.createElement("img");
    img.src = item.thumbnail_url;
    img.alt = item.title || "News thumbnail";
    img.loading = "lazy";
    img.onerror = function () {
      // Hide image and show placeholder on error
      this.style.display = "none";
      const placeholder = document.createElement("div");
      placeholder.className = "thumbnail-placeholder";
      placeholder.textContent = "No Image";
      thumbnail.appendChild(placeholder);
    };
    thumbnail.appendChild(img);
  } else {
    const placeholder = document.createElement("div");
    placeholder.className = "thumbnail-placeholder";
    placeholder.textContent = "No Image";
    thumbnail.appendChild(placeholder);
  }

  // Card content
  const content = document.createElement("div");
  content.className = "news-card-content";

  // Title
  const title = document.createElement("h3");
  title.className = "news-card-title";
  if (item.source_url) {
    const titleLink = document.createElement("a");
    titleLink.href = item.source_url;
    titleLink.target = "_blank";
    titleLink.rel = "noopener noreferrer";
    titleLink.textContent = item.title || "Untitled";
    title.appendChild(titleLink);
  } else {
    title.textContent = item.title || "Untitled";
  }

  // Summary
  const summary = document.createElement("p");
  summary.className = "news-card-summary";
  summary.textContent =
    item.summary || item.description || "No summary available.";

  // Visual tags (only tags we use - from categorization)
  if (item.visual_tags && item.visual_tags.length > 0) {
    const visualTagsContainer = document.createElement("div");
    visualTagsContainer.className = "news-card-visual-tags";
    item.visual_tags.slice(0, 3).forEach((tag) => {
      const tagElement = document.createElement("span");
      tagElement.className = "news-visual-tag";
      tagElement.textContent = tag;
      visualTagsContainer.appendChild(tagElement);
    });
    content.appendChild(visualTagsContainer);
  }

  // Source info
  const source = document.createElement("div");
  source.className = "news-card-meta";
  if (item.source) {
    const sourceText = document.createElement("span");
    sourceText.textContent = `Source: ${item.source}`;
    source.appendChild(sourceText);
  }
  if (item.published_date) {
    const dateText = document.createElement("span");
    dateText.textContent = formatDate(item.published_date);
    source.appendChild(dateText);
  }

  content.appendChild(title);
  content.appendChild(summary);
  content.appendChild(source);

  card.appendChild(thumbnail);
  card.appendChild(content);

  return card;
}

/**
 * Formats a date string for display
 * @param {string} dateString - ISO date string
 * @returns {string} Formatted date
 */
function formatDate(dateString) {
  if (!dateString) return "";
  try {
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch (e) {
    return dateString;
  }
}

/**
 * Updates the feed status badge
 * @param {string} status - 'loading', 'success', 'error', 'empty'
 * @param {string} message - Status message
 */
function updateFeedStatus(status, message) {
  const statusElement = document.getElementById("feed-status");
  if (!statusElement) return;

  statusElement.className = `status-badge ${status}`;
  statusElement.textContent = message;
}

/**
 * Updates the feed timestamp
 */
function updateFeedTimestamp() {
  const timestampElement = document.getElementById("feed-timestamp");
  if (!timestampElement) return;

  const now = new Date();
  timestampElement.textContent = now.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

/**
 * Updates video ideas status badge
 */
function updateVideoIdeasStatus(status, message) {
  const statusBadge = document.getElementById("video-ideas-status");
  if (!statusBadge) return;

  statusBadge.className = `status-badge ${status}`;
  statusBadge.textContent = message;
}

/**
 * Updates video ideas timestamp
 */
function updateVideoIdeasTimestamp() {
  const timestampEl = document.getElementById("video-ideas-timestamp");
  if (!timestampEl) return;

  const now = new Date();
  timestampEl.textContent = now.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

/**
 * Displays error message in the feed container
 * @param {string} errorMessage - Error message to display
 */
function displayError(errorMessage) {
  const errorContainer = document.getElementById("feed-error");
  const errorText = document.getElementById("error-text");
  const container = document.getElementById("feed-container");

  if (errorContainer && errorText) {
    errorText.textContent = errorMessage;
    errorContainer.style.display = "block";
  }

  if (container) {
    container.innerHTML = "";
  }

  updateFeedStatus("error", "Error");
}

/**
 * Sets up navigation click handlers
 */
function setupNavigation() {
  const navLinks = document.querySelectorAll(".nav-link");
  const sections = document.querySelectorAll(".content-section");

  navLinks.forEach((link) => {
    link.addEventListener("click", (e) => {
      const href = link.getAttribute("href");
      const targetSection = link.getAttribute("data-section");

      // Handle hash-based navigation
      if (href && href.startsWith("#")) {
        e.preventDefault();
        if (!targetSection) return;

        // Update URL hash without triggering navigation
        window.history.pushState(null, "", href);

        // Update active nav link
        navLinks.forEach((l) => l.classList.remove("active"));
        link.classList.add("active");

        // Show/hide sections
        sections.forEach((section) => {
          if (section.id === targetSection) {
            section.classList.add("active");
          } else {
            section.classList.remove("active");
          }
        });

        // Load section-specific content
        loadSectionContent(targetSection);
      }
    });
  });

  // Handle browser back/forward buttons
  window.addEventListener("popstate", () => {
    const hash = window.location.hash.slice(1) || "feed";
    const section = document.getElementById(hash);
    const navLink = document.querySelector(`[data-section="${hash}"]`);

    if (section && navLink) {
      // Update active nav link
      navLinks.forEach((l) => l.classList.remove("active"));
      navLink.classList.add("active");

      // Show/hide sections
      sections.forEach((s) => {
        if (s.id === hash) {
          s.classList.add("active");
        } else {
          s.classList.remove("active");
        }
      });

      // Load section content
      loadSectionContent(hash);
    }
  });
}

/**
 * Loads content for specific sections
 * @param {string} sectionId - Section ID to load
 */
async function loadSectionContent(sectionId) {
  switch (sectionId) {
    case "feed":
      await loadFeed();
      break;
    case "video-ideas":
      await loadVideoIdeas();
      break;
    case "output":
      await loadOutputFeed();
      break;
    // dashboard and rationale are static, no loading needed
  }
}

/**
 * Loads and displays the main feed
 */
async function loadFeed() {
  updateFeedStatus("loading", "Loading...");

  try {
    const feedData = await fetchFeed();
    currentFeedData = feedData;
    renderFeed(feedData);
  } catch (error) {
    displayError(
      error.message || "Failed to load feed. Please try again later."
    );
  }
}

/**
 * Loads and displays video ideas
 */
async function loadVideoIdeas() {
  const container = document.getElementById("video-ideas-container");
  const emptyContainer = document.getElementById("ideas-empty");

  if (!container) return;

  container.innerHTML =
    '<div class="loading-spinner"><div class="spinner"></div><p>Loading video ideas...</p></div>';
  if (emptyContainer) emptyContainer.style.display = "none";

  try {
    const feedData = await fetchFeed();
    let videoIdeas = feedData.filter(
      (item) => item.type === "video_idea" || item.video_idea
    );

    // Update tag filter buttons (use all video ideas to show all available tags)
    updateTagFilters(videoIdeas, "video-ideas-tag-filters");
    updateSourceFilters(videoIdeas, "video-ideas-source-filters");

    // Filter by tag if not "all"
    if (currentVideoIdeasTag !== "all") {
      videoIdeas = videoIdeas.filter((idea) => {
        const tags = idea.visual_tags || [];
        return tags.includes(currentVideoIdeasTag);
      });
    }

    // Filter by source if not "all"
    if (currentVideoIdeasSource !== "all") {
      videoIdeas = videoIdeas.filter((idea) => {
        const source = idea.source || "";
        return source.toLowerCase() === currentVideoIdeasSource.toLowerCase();
      });
    }

    container.innerHTML = "";

    if (videoIdeas.length === 0) {
      if (emptyContainer) emptyContainer.style.display = "block";
      updateVideoIdeasStatus("empty", "No items available");
      return;
    }

    // Update status
    updateVideoIdeasStatus("success", "Loaded");
    updateVideoIdeasTimestamp();

    // Render video ideas
    videoIdeas.forEach((idea) => {
      const card = createVideoIdeaCard(idea);
      container.appendChild(card);
    });

    // Setup search and sort
    setupVideoIdeasFilters(videoIdeas);
  } catch (error) {
    container.innerHTML = `<div class="error-message">Error loading video ideas: ${error.message}</div>`;
  }
}

/**
 * Creates a video idea card
 * @param {Object} idea - Video idea object
 * @returns {HTMLElement} Card element
 */
function createVideoIdeaCard(idea) {
  const card = document.createElement("div");
  card.className = "news-card"; // Use same styling as feed cards

  // Thumbnail - use news-card-image class to match CSS
  const thumbnail = document.createElement("div");
  thumbnail.className = "news-card-image";
  if (idea.thumbnail_url) {
    const img = document.createElement("img");
    img.src = idea.thumbnail_url;
    img.alt = idea.title || "Video idea thumbnail";
    img.loading = "lazy";
    img.onerror = function () {
      this.style.display = "none";
    };
    thumbnail.appendChild(img);
  }
  card.appendChild(thumbnail);

  // Content
  const content = document.createElement("div");
  content.className = "news-card-content";

  // Title
  const title = document.createElement("h3");
  title.className = "news-card-title";
  title.textContent = idea.title || "Untitled Video Idea";
  content.appendChild(title);

  // Description - for video ideas, always use description (video concept), never original_summary
  // For news items, use summary
  let descriptionText = "";
  if (idea.type === "video_idea") {
    // Video ideas should have description (the video concept), not original_summary
    descriptionText = idea.description || "";
  } else {
    // News items use summary
    descriptionText = idea.summary || idea.description || "";
  }
  
  if (descriptionText) {
    const desc = document.createElement("p");
    desc.className = "news-card-summary";
    desc.textContent = descriptionText;
    content.appendChild(desc);
  }

  // Meta information (source, scores, etc.)
  const meta = document.createElement("div");
  meta.className = "news-card-meta";

  if (idea.source) {
    const source = document.createElement("span");
    source.className = "news-card-source";
    source.textContent = idea.source;
    meta.appendChild(source);
  }

  // Add trend/SEO scores if available
  if (idea.trend_score !== undefined || idea.seo_score !== undefined) {
    const scores = document.createElement("span");
    scores.className = "news-card-scores";
    const scoreParts = [];
    if (idea.trend_score !== undefined) {
      scoreParts.push(`Trend: ${(idea.trend_score * 100).toFixed(0)}%`);
    }
    if (idea.seo_score !== undefined) {
      scoreParts.push(`SEO: ${(idea.seo_score * 100).toFixed(0)}%`);
    }
    scores.textContent = scoreParts.join(" • ");
    meta.appendChild(scores);
  }

  content.appendChild(meta);

  // Source URL link
  if (idea.source_url) {
    const link = document.createElement("a");
    link.href = idea.source_url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.className = "news-card-link";
    link.textContent = "Read more →";
    content.appendChild(link);
  }

  card.appendChild(content);
  return card;
}

/**
 * Sets up search and sort filters for video ideas
 * @param {Array} ideas - Array of video ideas
 */
function setupVideoIdeasFilters(ideas) {
  const searchInput = document.getElementById("idea-search");
  const sortSelect = document.getElementById("idea-sort");
  const container = document.getElementById("video-ideas-container");

  if (!searchInput || !sortSelect || !container) return;

  let filteredIdeas = [...ideas];

  const applyFilters = () => {
    // Search filter
    const searchTerm = searchInput.value.toLowerCase();
    filteredIdeas = ideas.filter((idea) => {
      const title = (idea.title || "").toLowerCase();
      const desc = (idea.description || "").toLowerCase();
      return title.includes(searchTerm) || desc.includes(searchTerm);
    });

    // Sort
    const sortBy = sortSelect.value;
    filteredIdeas.sort((a, b) => {
      switch (sortBy) {
        case "title":
          return (a.title || "").localeCompare(b.title || "");
        case "source":
          return (a.source || "").localeCompare(b.source || "");
        case "date":
        default:
          const dateA = new Date(a.published_date || a.date || 0);
          const dateB = new Date(b.published_date || b.date || 0);
          return dateB - dateA; // Latest first
      }
    });

    // Re-render
    container.innerHTML = "";
    if (filteredIdeas.length === 0) {
      const empty = document.getElementById("ideas-empty");
      if (empty) empty.style.display = "block";
    } else {
      filteredIdeas.forEach((idea) => {
        container.appendChild(createVideoIdeaCard(idea));
      });
    }
  };

  searchInput.addEventListener("input", applyFilters);
  sortSelect.addEventListener("change", applyFilters);
}

/**
 * Loads and displays the raw output feed (JSON)
 */
async function loadOutputFeed() {
  const outputElement = document.getElementById("output-feed");
  const prettyPrintCheckbox = document.getElementById("pretty-print");
  const downloadBtn = document.getElementById("btn-download");
  const copyBtn = document.getElementById("btn-copy");

  if (!outputElement) return;

  outputElement.textContent = "Loading feed.json...";

  try {
    const feedData = await fetchFeed();
    const isPretty = prettyPrintCheckbox ? prettyPrintCheckbox.checked : true;

    outputElement.textContent = isPretty
      ? JSON.stringify(feedData, null, 2)
      : JSON.stringify(feedData);

    // Setup download button
    if (downloadBtn) {
      downloadBtn.onclick = () => {
        const blob = new Blob([JSON.stringify(feedData, null, 2)], {
          type: "application/json",
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "feed.json";
        a.click();
        URL.revokeObjectURL(url);
      };
    }

    // Setup copy button
    if (copyBtn) {
      copyBtn.onclick = async () => {
        try {
          await navigator.clipboard.writeText(
            JSON.stringify(feedData, null, 2)
          );
          copyBtn.textContent = "Copied!";
          setTimeout(() => {
            copyBtn.textContent = "Copy to Clipboard";
          }, 2000);
        } catch (err) {
          console.error("Failed to copy:", err);
        }
      };
    }

    // Setup pretty print toggle
    if (prettyPrintCheckbox) {
      prettyPrintCheckbox.addEventListener("change", () => {
        outputElement.textContent = prettyPrintCheckbox.checked
          ? JSON.stringify(feedData, null, 2)
          : JSON.stringify(feedData);
      });
    }
  } catch (error) {
    outputElement.textContent = `Error loading feed: ${error.message}`;
  }
}

/**
 * Starts the auto-refresh timer
 */
function startAutoRefresh() {
  // Clear existing timer if any
  if (refreshTimer) {
    clearInterval(refreshTimer);
  }

  // Set up new timer
  refreshTimer = setInterval(async () => {
    const activeSection = document.querySelector(".content-section.active");
    if (activeSection && activeSection.id === "feed") {
      try {
        const feedData = await fetchFeed();
        currentFeedData = feedData;
        renderFeed(feedData);
      } catch (error) {
        console.error("Auto-refresh error:", error);
        // Don't show error on auto-refresh, just log it
      }
    }
  }, REFRESH_INTERVAL);

  console.log(
    `Auto-refresh started (every ${REFRESH_INTERVAL / 1000 / 60} minutes)`
  );
}

/**
 * Initializes the application when DOM is ready
 */
function initialize() {
  // Setup navigation first
  setupNavigation();

  // Check hash or default to feed
  const hash = window.location.hash.slice(1);
  const initialSection = hash || "feed";

  // Activate the correct section
  const section = document.getElementById(initialSection);
  const navLink = document.querySelector(`[data-section="${initialSection}"]`);

  if (section && navLink) {
    // Hide all sections
    document.querySelectorAll(".content-section").forEach((s) => {
      s.classList.remove("active");
    });
    // Show target section
    section.classList.add("active");
    // Update nav
    document.querySelectorAll(".nav-link").forEach((l) => {
      l.classList.remove("active");
    });
    navLink.classList.add("active");
    // Load section content
    loadSectionContent(initialSection);
  } else {
    // Fallback: load feed
    loadFeed();
  }

  // Setup tag filters
  setupTagFilters();

  // Start auto-refresh
  startAutoRefresh();

  console.log("AI News Tracker initialized");
}

/**
 * Updates tag filter buttons based on available tags in data
 */
function updateTagFilters(data, filterContainerId) {
  const container = document.getElementById(filterContainerId);
  if (!container) return;

  // Collect all unique tags from data
  const allTags = new Set();
  data.forEach((item) => {
    const tags = item.visual_tags || [];
    tags.forEach((tag) => allTags.add(tag));
  });

  // Get existing buttons (keep "All" button)
  const existingButtons = Array.from(container.querySelectorAll(".filter-btn"));
  const allButton = existingButtons.find((btn) => btn.dataset.tag === "all");

  // Clear container but keep "All" button
  container.innerHTML = "";
  if (allButton) {
    container.appendChild(allButton);
  }

  // Add buttons for each tag
  const sortedTags = Array.from(allTags).sort();
  sortedTags.forEach((tag) => {
    const btn = document.createElement("button");
    btn.className = "filter-btn";
    btn.dataset.tag = tag;
    btn.textContent = tag;
    if (tag === (filterContainerId === "feed-tag-filters" ? currentFeedTag : currentVideoIdeasTag)) {
      btn.classList.add("active");
    }
    container.appendChild(btn);
  });
}

/**
 * Updates source filter buttons based on available sources in data
 */
function updateSourceFilters(data, filterContainerId) {
  const container = document.getElementById(filterContainerId);
  if (!container) return;

  // Collect all unique sources from data
  const allSources = new Set();
  data.forEach((item) => {
    const source = item.source || "";
    if (source) {
      allSources.add(source);
    }
  });

  // Get existing buttons (keep "All" button)
  const existingButtons = Array.from(container.querySelectorAll(".filter-btn"));
  const allButton = existingButtons.find((btn) => btn.dataset.source === "all");

  // Clear container but keep "All" button
  container.innerHTML = "";
  if (allButton) {
    container.appendChild(allButton);
  }

  // Add buttons for each source
  const sortedSources = Array.from(allSources).sort();
  sortedSources.forEach((source) => {
    const btn = document.createElement("button");
    btn.className = "filter-btn";
    btn.dataset.source = source;
    btn.textContent = source;
    const currentSource = filterContainerId === "feed-source-filters" ? currentFeedSource : currentVideoIdeasSource;
    if (source === currentSource) {
      btn.classList.add("active");
    }
    container.appendChild(btn);
  });
}

/**
 * Sets up tag filter buttons for feed and video ideas
 */
function setupTagFilters() {
  // Feed tag filters
  const feedFilters = document.getElementById("feed-tag-filters");
  if (feedFilters) {
    feedFilters.addEventListener("click", (e) => {
      if (e.target.classList.contains("filter-btn")) {
        // Update active state
        feedFilters.querySelectorAll(".filter-btn").forEach((btn) => {
          btn.classList.remove("active");
        });
        e.target.classList.add("active");

        // Update filter
        currentFeedTag = e.target.dataset.tag;

        // Re-render feed with new filter
        if (currentFeedData.length > 0) {
          renderFeed(currentFeedData);
        }
      }
    });
  }

  // Feed source filters
  const feedSourceFilters = document.getElementById("feed-source-filters");
  if (feedSourceFilters) {
    feedSourceFilters.addEventListener("click", (e) => {
      if (e.target.classList.contains("filter-btn")) {
        // Update active state
        feedSourceFilters.querySelectorAll(".filter-btn").forEach((btn) => {
          btn.classList.remove("active");
        });
        e.target.classList.add("active");

        // Update filter
        currentFeedSource = e.target.dataset.source;

        // Re-render feed with new filter
        if (currentFeedData.length > 0) {
          renderFeed(currentFeedData);
        }
      }
    });
  }

  // Video ideas tag filters
  const videoIdeasFilters = document.getElementById("video-ideas-tag-filters");
  if (videoIdeasFilters) {
    videoIdeasFilters.addEventListener("click", (e) => {
      if (e.target.classList.contains("filter-btn")) {
        // Update active state
        videoIdeasFilters.querySelectorAll(".filter-btn").forEach((btn) => {
          btn.classList.remove("active");
        });
        e.target.classList.add("active");

        // Update filter
        currentVideoIdeasTag = e.target.dataset.tag;

        // Re-render video ideas with new filter
        loadVideoIdeas();
      }
    });
  }
}


// Initialize when DOM is ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initialize);
} else {
  // DOM is already ready
  initialize();
}
