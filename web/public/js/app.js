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

  // Render each feed item as a card
  feedData.forEach((item) => {
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

  // Thumbnail
  const thumbnail = document.createElement("div");
  thumbnail.className = "card-thumbnail";
  if (item.thumbnail_url) {
    const img = document.createElement("img");
    img.src = item.thumbnail_url;
    img.alt = item.title || "News thumbnail";
    img.loading = "lazy";
    img.onerror = function () {
      this.style.display = "none";
    };
    thumbnail.appendChild(img);
  } else {
    thumbnail.innerHTML = '<div class="thumbnail-placeholder">No Image</div>';
  }

  // Card content
  const content = document.createElement("div");
  content.className = "card-content";

  // Title
  const title = document.createElement("h3");
  title.className = "card-title";
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
  summary.className = "card-summary";
  summary.textContent =
    item.summary || item.description || "No summary available.";

  // Source info
  const source = document.createElement("div");
  source.className = "card-source";
  if (item.source) {
    const sourceText = document.createElement("span");
    sourceText.textContent = `Source: ${item.source}`;
    source.appendChild(sourceText);
  }
  if (item.published_date) {
    const dateText = document.createElement("span");
    dateText.className = "card-date";
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
      e.preventDefault();

      const targetSection = link.getAttribute("data-section");
      if (!targetSection) return;

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
    });
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
    const videoIdeas = feedData.filter(
      (item) => item.type === "video_idea" || item.video_idea
    );

    container.innerHTML = "";

    if (videoIdeas.length === 0) {
      if (emptyContainer) emptyContainer.style.display = "block";
      return;
    }

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
  card.className = "idea-card";

  if (idea.thumbnail_url || idea.thumbnail_path) {
    const img = document.createElement("img");
    img.src = idea.thumbnail_url || idea.thumbnail_path;
    img.alt = idea.title || "Video idea thumbnail";
    img.className = "idea-thumbnail";
    img.loading = "lazy";
    card.appendChild(img);
  }

  const content = document.createElement("div");
  content.className = "idea-content";

  const title = document.createElement("h3");
  title.textContent = idea.title || "Untitled Video Idea";
  content.appendChild(title);

  if (idea.description) {
    const desc = document.createElement("p");
    desc.textContent = idea.description;
    content.appendChild(desc);
  }

  if (idea.source) {
    const source = document.createElement("span");
    source.className = "idea-source";
    source.textContent = `Source: ${idea.source}`;
    content.appendChild(source);
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
 * Updates URLs to use the current page protocol (HTTP/HTTPS)
 */
function updateProtocolAwareUrls() {
  const protocol = window.location.protocol;
  const isHttps = protocol === "https:";

  // Update n8n dashboard iframe
  const n8nIframe = document.getElementById("n8n-iframe");
  if (n8nIframe) {
    // Use same protocol as current page, but note: n8n might not support HTTPS
    // For now, keep HTTP for n8n since it's on a different port
    n8nIframe.src = "http://localhost:5678";
  }

  // Update n8n URL display
  const n8nUrlSpan = document.getElementById("n8n-url");
  if (n8nUrlSpan) {
    n8nUrlSpan.textContent = "http://localhost:5678";
  }

  // Update footer links to use current protocol
  const footerN8nLink = document.getElementById("footer-n8n-link");
  if (footerN8nLink) {
    footerN8nLink.href = "http://localhost:5678";
  }

  // Health check link is already relative (/api/health), so it will use current protocol
  // No update needed - relative URLs automatically use the same protocol
}

/**
 * Initializes the application when DOM is ready
 */
function initialize() {
  // Update protocol-aware URLs
  updateProtocolAwareUrls();

  // Setup navigation
  setupNavigation();

  // Load initial feed
  loadFeed();

  // Start auto-refresh
  startAutoRefresh();

  console.log("AI News Tracker initialized");
}

// Initialize when DOM is ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initialize);
} else {
  // DOM is already ready
  initialize();
}
