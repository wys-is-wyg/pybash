/**
 * AI News Tracker - Frontend Application
 * Handles feed fetching, rendering, navigation, and auto-refresh
 */

// API base URL - use relative path since server.js proxies /api to python-app
const API_BASE_URL = "/api";

// Auto-refresh interval (5 minutes = 300000ms)
const REFRESH_INTERVAL = 300000;

// State management
let currentFeedData = null; // Will store { data: {...}, items: [...] }
let feedDataLookup = {}; // Centralized data lookup by article_id
let refreshTimer = null;
let currentFeedTag = "all";
let currentFeedSource = "all";

/**
 * Fetches feed data from the API
 * @returns {Promise<Object>} Object with { data: {...}, items: [...] } structure
 */
async function fetchFeed() {
  try {
    const response = await fetch(`${API_BASE_URL}/news`);

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();

    // Expect new structure with centralized data lookup
    if (data && data.data && data.items) {
      return data;
    }

    // If structure is wrong, return empty
    console.error(
      "Invalid data structure: expected { data: {...}, items: [...] }"
    );
    return { data: {}, items: [] };
  } catch (error) {
    console.error("Error fetching feed:", error);
    throw error;
  }
}

/**
 * Renders feed items into the feed container
 * @param {Object} feedData - Object with { data: {...}, items: [...] } structure
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

  // Store feed data and lookup globally
  currentFeedData = feedData;
  feedDataLookup = feedData.data || {};

  // Handle empty feed
  const items = feedData.items || [];
  if (!items || items.length === 0) {
    if (emptyContainer) emptyContainer.style.display = "block";
    updateFeedStatus("empty", "No items available");
    return;
  }

  // Update status
  updateFeedStatus("success", "Loaded");
  updateFeedTimestamp();

  // Build full items with data for filtering
  const fullItems = items.map((item) => {
    const articleData = feedDataLookup[item.article_id] || {};
    return { ...item, ...articleData };
  });

  // Update tag filter buttons (use all data to show all available tags)
  updateTagFilters(fullItems, "feed-tag-filters");

  // Filter by tag if not "all"
  let filteredItems = items;
  if (currentFeedTag !== "all") {
    filteredItems = filteredItems.filter((item) => {
      const articleData = feedDataLookup[item.article_id] || {};
      const tags = articleData.visual_tags || [];
      return tags.includes(currentFeedTag);
    });
  }

  // Filter by source if not "all"
  if (currentFeedSource !== "all") {
    filteredItems = filteredItems.filter((item) => {
      const articleData = feedDataLookup[item.article_id] || {};
      const source = articleData.source || "";
      return source.toLowerCase() === currentFeedSource.toLowerCase();
    });
  }

  // Render each feed item as a card
  filteredItems.forEach((item) => {
    const card = createFeedCard(item);
    container.appendChild(card);
  });
}

/**
 * Creates a feed card element from an item (using Video Ideas card design)
 * @param {Object} item - Minimal item with article_id, type, video_ideas
 * @returns {HTMLElement} Card element
 */
function createFeedCard(item) {
  // Get full article data from centralized lookup
  const articleData = feedDataLookup[item.article_id] || {};

  const card = document.createElement("div");
  card.className = "news-card";
  card.style.cursor = "pointer";
  card.onclick = function (e) {
    // Don't open modal if clicking on a link or inside a link (let link handle it)
    if (e.target.tagName === "A" || e.target.closest("a")) {
      return;
    }
    openSummaryModal(item.article_id);
  };

  // Thumbnail
  const thumbnail = document.createElement("div");
  thumbnail.className = "news-card-image";
  if (articleData.thumbnail_url) {
    const img = document.createElement("img");
    img.src = articleData.thumbnail_url;
    img.alt = articleData.title || "News thumbnail";
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

  // Article title (opens modal)
  const articleTitle = document.createElement("h3");
  articleTitle.className = "news-card-title";
  const articleTitleText = articleData.title || "Untitled Article";
  if (articleData.source_url || articleData.summary) {
    const titleLink = document.createElement("a");
    titleLink.href = "#";
    titleLink.textContent = articleTitleText;
    titleLink.onclick = function (e) {
      e.preventDefault();
      e.stopPropagation();
      openSummaryModal(item.article_id);
    };
    articleTitle.appendChild(titleLink);
  } else {
    articleTitle.textContent = articleTitleText;
  }
  content.appendChild(articleTitle);

  // Article summary (short summary)
  if (articleData.summary) {
    const summary = document.createElement("p");
    summary.className = "news-card-summary";
    summary.textContent = articleData.summary;
    content.appendChild(summary);
  }

  // Video ideas section - display all video ideas from the array
  const videoIdeas = item.video_ideas || [];
  if (videoIdeas.length > 0) {
    const videoIdeasSection = document.createElement("div");
    videoIdeasSection.className = "video-ideas-section";

    videoIdeas.forEach((idea, index) => {
      if (idea.title || idea.description) {
        if (idea.title) {
          const videoIdeaTitle = document.createElement("h4");
          videoIdeaTitle.className = "video-idea-title";
          videoIdeaTitle.textContent = idea.title;
          videoIdeasSection.appendChild(videoIdeaTitle);
        }

        if (idea.description) {
          const videoIdeaDesc = document.createElement("p");
          videoIdeaDesc.className = "video-idea-description";
          videoIdeaDesc.textContent = idea.description;
          videoIdeasSection.appendChild(videoIdeaDesc);
        }
      }
    });

    if (videoIdeasSection.children.length > 0) {
      content.appendChild(videoIdeasSection);
    }
  }

  // Meta information (source, date, and Read More link)
  const meta = document.createElement("div");
  meta.className = "news-card-meta";

  if (articleData.published_date) {
    const dateText = document.createElement("span");
    dateText.textContent = formatDate(articleData.published_date);
    meta.appendChild(dateText);
  }

  // Read More link (opens modal)
  if (articleData.summary) {
    const readMoreLink = document.createElement("a");
    readMoreLink.href = "#";
    readMoreLink.className = "news-card-article-link";
    readMoreLink.textContent = "Read More →";
    readMoreLink.onclick = function (e) {
      e.preventDefault();
      e.stopPropagation();
      openSummaryModal(item.article_id);
    };
    meta.appendChild(readMoreLink);
  } else if (articleData.source_url) {
    // Fallback: open modal even if no summary
    const articleLink = document.createElement("a");
    articleLink.href = "#";
    articleLink.className = "news-card-article-link";
    articleLink.textContent = "Read Article →";
    articleLink.onclick = function (e) {
      e.preventDefault();
      e.stopPropagation();
      openSummaryModal(item.article_id);
    };
    meta.appendChild(articleLink);
  }

  if (articleData.source) {
    const source = document.createElement("span");
    source.className = "news-card-source";
    source.textContent = articleData.source;
    meta.appendChild(source);
  }

  content.appendChild(meta);
  card.appendChild(content);

  return card;
}

/**
 * Opens a modal with the complete blog article summary
 * @param {string} articleId - Article ID to look up
 */
function openSummaryModal(articleId) {
  const articleData = feedDataLookup[articleId];
  if (!articleData) {
    return;
  }

  // Find the item to get video ideas
  const item = currentFeedData?.items?.find((i) => i.article_id === articleId);
  const videoIdeas = item?.video_ideas || [];

  // Create or get modal
  let modal = document.getElementById("summary-modal");
  if (!modal) {
    modal = document.createElement("div");
    modal.id = "summary-modal";
    modal.className = "summary-modal";
    modal.innerHTML = `
      <div class="summary-modal-content">
        <div class="summary-modal-header">
          <button class="summary-modal-close" id="summary-modal-close">&times;</button>
        </div>
        <div class="summary-modal-body">
          <div class="summary-modal-top-section">
            <div id="summary-modal-image" class="summary-modal-image-container"></div>
            <div class="summary-modal-right-content">
              <h2 id="summary-modal-title" class="summary-modal-title"></h2>
              <div id="summary-modal-content" class="summary-modal-summary"></div>
            </div>
          </div>
          <div id="summary-modal-video-ideas" class="summary-modal-video-ideas-container"></div>
        </div>
        <div class="summary-modal-footer">
          <a id="summary-modal-link" href="#" target="_blank" class="btn-primary">Read Full Article →</a>
        </div>
      </div>
    `;
    document.body.appendChild(modal);

    // Close handlers
    const closeBtn = document.getElementById("summary-modal-close");
    closeBtn.onclick = function () {
      modal.classList.remove("active");
    };
    modal.onclick = function (e) {
      if (e.target === modal) {
        modal.classList.remove("active");
      }
    };

    // Close on Escape key
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && modal.classList.contains("active")) {
        modal.classList.remove("active");
      }
    });
  }

  // Populate image
  const imageEl = document.getElementById("summary-modal-image");
  imageEl.innerHTML = "";
  if (articleData.thumbnail_url) {
    const img = document.createElement("img");
    img.src = articleData.thumbnail_url;
    img.alt = articleData.title || "Article thumbnail";
    img.className = "summary-modal-image";
    img.onerror = function () {
      this.style.display = "none";
    };
    imageEl.appendChild(img);
  }

  // Populate title (orange, linked to article)
  const titleEl = document.getElementById("summary-modal-title");
  titleEl.innerHTML = "";
  const titleText = articleData.title || "Article Summary";
  if (articleData.source_url) {
    const titleLink = document.createElement("a");
    titleLink.href = articleData.source_url;
    titleLink.target = "_blank";
    titleLink.rel = "noopener noreferrer";
    titleLink.textContent = titleText;
    titleLink.className = "summary-modal-title-link";
    titleEl.appendChild(titleLink);
  } else {
    titleEl.textContent = titleText;
    titleEl.className = "summary-modal-title-text";
  }

  // Populate summary
  const contentEl = document.getElementById("summary-modal-content");
  if (articleData.summary) {
    contentEl.innerHTML = `<div class="summary-content">${escapeHtml(
      articleData.summary
    )}</div>`;
  } else {
    contentEl.innerHTML =
      '<div class="summary-content">No summary available.</div>';
  }

  // Populate video ideas (full width, below with orange separator)
  const videoIdeasEl = document.getElementById("summary-modal-video-ideas");
  videoIdeasEl.innerHTML = "";
  if (videoIdeas.length > 0) {
    let videoIdeasHTML =
      '<div class="summary-video-ideas"><h3>Video Ideas</h3>';
    videoIdeas.forEach((idea, index) => {
      videoIdeasHTML += '<div class="summary-video-idea">';
      if (idea.title) {
        videoIdeasHTML += `<h4 class="summary-video-idea-title">${escapeHtml(
          idea.title
        )}</h4>`;
      }
      if (idea.description) {
        videoIdeasHTML += `<p class="summary-video-idea-description">${escapeHtml(
          idea.description
        )}</p>`;
      }
      videoIdeasHTML += "</div>";
    });
    videoIdeasHTML += "</div>";
    videoIdeasEl.innerHTML = videoIdeasHTML;
  }

  // Populate footer link
  const linkEl = document.getElementById("summary-modal-link");
  if (articleData.source_url) {
    linkEl.href = articleData.source_url;
    linkEl.style.display = "inline-block";
  } else {
    linkEl.style.display = "none";
  }

  // Show modal with fade-in animation
  modal.classList.add("active");
}

/**
 * Escapes HTML to prevent XSS
 * @param {string} text - Text to escape
 * @returns {string} Escaped text
 */
function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
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

        // Show/hide sections with fade transition
        sections.forEach((section) => {
          if (section.id === targetSection) {
            // Fade in new section
            section.style.display = "block";
            // Force reflow to ensure display is set before animation
            requestAnimationFrame(() => {
              requestAnimationFrame(() => {
                section.classList.add("active");
              });
            });
          } else {
            // Fade out old section, then remove from flow
            if (section.classList.contains("active")) {
              section.classList.remove("active");
              // Wait for fade out animation to complete
              setTimeout(() => {
                section.style.display = "none";
              }, 400); // Match CSS animation duration
            } else {
              section.style.display = "none";
            }
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

      // Show/hide sections with fade transition
      sections.forEach((s) => {
        if (s.id === hash) {
          // Fade in new section
          s.style.display = "block";
          // Force reflow to ensure display is set before animation
          requestAnimationFrame(() => {
            requestAnimationFrame(() => {
              s.classList.add("active");
            });
          });
        } else {
          // Fade out old section, then remove from flow
          if (s.classList.contains("active")) {
            s.classList.remove("active");
            // Wait for fade out transition to complete
            setTimeout(() => {
              s.style.display = "none";
            }, 400); // Match CSS transition duration
          } else {
            s.style.display = "none";
          }
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
    case "output":
      await loadOutputFeed();
      break;
    case "contact":
      // Contact form is static, no loading needed
      break;
    // rationale is static, no loading needed
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
    // Filter for news items that have video ideas attached
    let videoIdeas = feedData.filter(
      (item) =>
        item.video_ideas &&
        Array.isArray(item.video_ideas) &&
        item.video_ideas.length > 0
    );

    // Update tag filter buttons (use all video ideas to show all available tags)
    updateTagFilters(videoIdeas, "video-ideas-tag-filters");

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
    // Use textContent to prevent XSS - don't use innerHTML with user-controlled data
    const errorDiv = document.createElement("div");
    errorDiv.className = "error-message";
    errorDiv.textContent = `Error loading video ideas: ${error.message}`;
    container.innerHTML = ""; // Clear container first
    container.appendChild(errorDiv);
  }
}

/**
 * Creates a video idea card
 * @param {Object} item - News item with video_ideas array
 * @returns {HTMLElement} Card element
 */
function createVideoIdeaCard(item) {
  const card = document.createElement("div");
  card.className = "news-card"; // Use same styling as feed cards

  // Thumbnail - use news-card-image class to match CSS
  const thumbnail = document.createElement("div");
  thumbnail.className = "news-card-image";
  if (item.thumbnail_url) {
    const img = document.createElement("img");
    img.src = item.thumbnail_url;
    img.alt = item.title || "Video idea thumbnail";
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

  // Article title (original article this video idea is based on)
  const articleTitle = document.createElement("h3");
  articleTitle.className = "news-card-title";
  const articleTitleText = item.title || "Untitled Article";
  if (item.source_url) {
    const titleLink = document.createElement("a");
    titleLink.href = item.source_url;
    titleLink.target = "_blank";
    titleLink.rel = "noopener noreferrer";
    titleLink.textContent = articleTitleText;
    articleTitle.appendChild(titleLink);
  } else {
    articleTitle.textContent = articleTitleText;
  }
  content.appendChild(articleTitle);

  // Article summary (if available)
  if (item.summary) {
    const summary = document.createElement("p");
    summary.className = "news-card-summary";
    summary.textContent = item.summary;
    content.appendChild(summary);
  }

  // Video ideas section - display all video ideas from the array
  const videoIdeasSection = document.createElement("div");
  videoIdeasSection.className = "video-ideas-section";

  const videoIdeas = item.video_ideas || [];
  if (videoIdeas.length > 0) {
    videoIdeas.forEach((idea, index) => {
      if (idea.title || idea.description) {
        if (idea.title) {
          const videoIdeaTitle = document.createElement("h4");
          videoIdeaTitle.className = "video-idea-title";
          videoIdeaTitle.textContent = idea.title;
          videoIdeasSection.appendChild(videoIdeaTitle);
        }

        if (idea.description) {
          const videoIdeaDesc = document.createElement("p");
          videoIdeaDesc.className = "video-idea-description";
          videoIdeaDesc.textContent = idea.description;
          videoIdeasSection.appendChild(videoIdeaDesc);
        }
      }
    });
  }

  if (videoIdeasSection.children.length > 0) {
    content.appendChild(videoIdeasSection);
  }

  // Meta information (source and date)
  const meta = document.createElement("div");
  meta.className = "news-card-meta";

  if (item.published_date) {
    const dateText = document.createElement("span");
    dateText.textContent = formatDate(item.published_date);
    meta.appendChild(dateText);
  }

  if (item.source_url) {
    const articleLink = document.createElement("a");
    articleLink.href = item.source_url;
    articleLink.target = "_blank";
    articleLink.rel = "noopener noreferrer";
    articleLink.className = "news-card-article-link";
    articleLink.textContent = "Read Article →";
    meta.appendChild(articleLink);
  }

  if (item.source) {
    const source = document.createElement("span");
    source.className = "news-card-source";
    source.textContent = item.source;
    meta.appendChild(source);
  }

  content.appendChild(meta);

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
    filteredIdeas = ideas.filter((item) => {
      // Search in article title and summary
      const title = (item.title || "").toLowerCase();
      const summary = (item.summary || "").toLowerCase();

      // Search in video ideas titles and descriptions
      const videoIdeas = item.video_ideas || [];
      const videoIdeasText = videoIdeas
        .map((idea) =>
          ((idea.title || "") + " " + (idea.description || "")).toLowerCase()
        )
        .join(" ");

      return (
        title.includes(searchTerm) ||
        summary.includes(searchTerm) ||
        videoIdeasText.includes(searchTerm)
      );
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
    // Hide all sections (remove from DOM flow)
    document.querySelectorAll(".content-section").forEach((s) => {
      s.classList.remove("active");
      s.style.display = "none";
    });
    // Show target section with fade in
    section.style.display = "block";
    // Force reflow to ensure display is set before animation
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        section.classList.add("active");
      });
    });
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
    if (tag === currentFeedTag) {
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
        if (currentFeedData && currentFeedData.items) {
          renderFeed(currentFeedData);
        }
      }
    });
  }
}

/**
 * Sets up contact form submission handler
 */
function setupContactForm() {
  const contactForm = document.getElementById("contact-form");
  if (!contactForm) return;

  const submitBtn = document.getElementById("contact-submit");
  const statusDiv = document.getElementById("contact-message-status");

  contactForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    // Disable submit button
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = "Sending...";
    }

    // Hide previous status messages
    if (statusDiv) {
      statusDiv.style.display = "none";
      statusDiv.className = "form-message";
    }

    // Get form data
    const formData = {
      name: document.getElementById("contact-name").value.trim(),
      email: document.getElementById("contact-email").value.trim(),
      subject: document.getElementById("contact-subject").value.trim(),
      message: document.getElementById("contact-message").value.trim(),
    };

    try {
      const response = await fetch(`${API_BASE_URL}/contact`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(formData),
      });

      const data = await response.json();

      if (response.ok && data.status === "success") {
        // Success
        if (statusDiv) {
          statusDiv.textContent =
            data.message || "Your message has been sent successfully!";
          statusDiv.className = "form-message success";
          statusDiv.style.display = "block";
        }

        // Reset form
        contactForm.reset();

        // Re-enable submit button after a delay
        setTimeout(() => {
          if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = "Send Message";
          }
        }, 2000);
      } else {
        // Error
        if (statusDiv) {
          statusDiv.textContent =
            data.error || "Failed to send message. Please try again.";
          statusDiv.className = "form-message error";
          statusDiv.style.display = "block";
        }

        // Re-enable submit button
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = "Send Message";
        }
      }
    } catch (error) {
      console.error("Error submitting contact form:", error);

      if (statusDiv) {
        statusDiv.textContent =
          "Network error. Please check your connection and try again.";
        statusDiv.className = "form-message error";
        statusDiv.style.display = "block";
      }

      // Re-enable submit button
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = "Send Message";
      }
    }
  });
}

// Password Modal Functions
function showPasswordModal() {
  const modal = document.getElementById("password-modal");
  const passwordInput = document.getElementById("password-input");
  const passwordError = document.getElementById("password-error");

  if (!modal) return;

  modal.classList.add("show");
  passwordInput.value = "";
  passwordInput.focus();
  passwordError.style.display = "none";

  // Close modal handlers
  const closeBtn = document.getElementById("password-modal-close");
  const cancelBtn = document.getElementById("password-cancel-btn");

  const closeModal = () => {
    modal.classList.remove("show");
  };

  if (closeBtn) closeBtn.onclick = closeModal;
  if (cancelBtn) cancelBtn.onclick = closeModal;

  // Close on background click
  modal.onclick = (e) => {
    if (e.target === modal) closeModal();
  };

  // Submit on Enter key
  passwordInput.onkeypress = (e) => {
    if (e.key === "Enter") {
      document.getElementById("password-submit-btn").click();
    }
  };
}

async function validatePasswordAndTriggerPipeline(password) {
  const triggerBtn = document.getElementById("trigger-pipeline-btn");
  const modal = document.getElementById("password-modal");
  const passwordError = document.getElementById("password-error");

  try {
    // Validate password with backend
    const response = await fetch(`${API_BASE_URL}/validate-pipeline-password`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ password }),
    });

    const data = await response.json();

    if (!response.ok || !data.valid) {
      passwordError.textContent = data.message || "Invalid password";
      passwordError.style.display = "block";
      document.getElementById("password-input").value = "";
      document.getElementById("password-input").focus();
      return false;
    }

    // Password valid - close modal and trigger pipeline
    modal.classList.remove("show");
    return true;
  } catch (error) {
    passwordError.textContent = "Error validating password. Please try again.";
    passwordError.style.display = "block";
    return false;
  }
}

// Trigger Pipeline Button Handler with Progress Tracking
function setupTriggerPipelineButton() {
  const triggerBtn = document.getElementById("trigger-pipeline-btn");
  if (!triggerBtn) return;

  // Set up password submit handler once
  const submitBtn = document.getElementById("password-submit-btn");
  if (submitBtn) {
    submitBtn.onclick = async () => {
      const passwordInput = document.getElementById("password-input");
      const password = passwordInput.value.trim();

      if (!password) {
        document.getElementById("password-error").textContent =
          "Please enter a password";
        document.getElementById("password-error").style.display = "block";
        return;
      }

      submitBtn.disabled = true;
      submitBtn.textContent = "Validating...";

      const isValid = await validatePasswordAndTriggerPipeline(password);

      submitBtn.disabled = false;
      submitBtn.textContent = "Submit";

      if (isValid) {
        // Close modal and trigger pipeline
        document.getElementById("password-modal").classList.remove("show");
        await triggerPipelineExecution(triggerBtn);
      }
    };
  }

  triggerBtn.addEventListener("click", async function () {
    // Show password modal first
    passwordValidated = false;
    showPasswordModal();
  });

  // Separate function to trigger pipeline execution
  async function triggerPipelineExecution(triggerBtn) {
    // Disable button and show loading state
    triggerBtn.disabled = true;
    triggerBtn.classList.add("loading");
    triggerBtn.textContent = "Starting...";

    let localProgressInterval = null;

    try {
      // Trigger pipeline
      const response = await fetch(`${API_BASE_URL}/trigger-pipeline`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });

      const data = await response.json();

      if (!response.ok || data.status !== "success") {
        throw new Error(data.message || "Failed to start pipeline");
      }

      // Start polling progress
      localProgressInterval = setInterval(async () => {
        try {
          const progressResponse = await fetch(
            `${API_BASE_URL}/pipeline-progress`
          );
          const progress = await progressResponse.json();

          if (progress.status === "running") {
            // Update button text with progress
            const percent = progress.progress_percent || 0;
            const step = progress.current_step || "";
            const remaining = progress.estimated_seconds_remaining || 0;

            let timeText = "";
            if (remaining > 0) {
              if (remaining < 60) {
                timeText = `~${remaining}s left`;
              } else {
                const minutes = Math.floor(remaining / 60);
                const seconds = remaining % 60;
                timeText = `~${minutes}m ${seconds}s left`;
              }
            }

            triggerBtn.textContent = `${step} (${percent}%) ${timeText}`.trim();
          } else if (progress.status === "completed") {
            // Pipeline completed
            clearInterval(localProgressInterval);
            triggerBtn.textContent = "Completed! Refreshing...";
            setTimeout(() => {
              window.location.reload(true); // Hard refresh
            }, 1000);
          } else if (progress.status === "error") {
            // Pipeline failed
            clearInterval(localProgressInterval);
            triggerBtn.textContent = "Error - Click to retry";
            triggerBtn.disabled = false;
            triggerBtn.classList.remove("loading");
            alert(`Pipeline error: ${progress.message || "Unknown error"}`);
          }
        } catch (error) {
          console.error("Error polling progress:", error);
        }
      }, 2000); // Poll every 2 seconds

      // Maximum timeout (30 minutes)
      setTimeout(() => {
        if (localProgressInterval) {
          clearInterval(localProgressInterval);
        }
        triggerBtn.textContent = "Taking longer than expected...";
        setTimeout(() => {
          window.location.reload(true); // Hard refresh
        }, 2000);
      }, 1800000); // 30 minutes max
    } catch (error) {
      if (localProgressInterval) {
        clearInterval(localProgressInterval);
      }
      console.error("Error triggering pipeline:", error);
      triggerBtn.textContent = "Error - Click to retry";
      triggerBtn.disabled = false;
      triggerBtn.classList.remove("loading");
      alert(`Failed to trigger pipeline: ${error.message}`);
    }
  }
}

// Initialize when DOM is ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", function () {
    initialize();
    setupTriggerPipelineButton();
    setupContactForm();
  });
} else {
  // DOM is already ready
  initialize();
  setupTriggerPipelineButton();
  setupContactForm();
}
