# AI News Tracker - Project Description

## 300-Word Description

**AI News Tracker** is an automated AI news aggregation and video idea generation platform that solves the problem of information overload in the fast-moving AI space. Built with modern web technologies and hosted on Hostinger VPS, it continuously monitors RSS feeds, social media, and AI company announcements to deliver curated, summarized news with AI-generated video concepts.

The system operates on a fully automated pipeline: Python scripts scrape news from multiple sources every 6 hours, AI models (including Llama 3.2) summarize articles, and a custom video idea generator transforms summaries into actionable content concepts. Each idea comes with a unique thumbnail generated via Leonardo AI API, creating a complete content package ready for production.

The architecture leverages Docker containers for isolation and scalability, with a Flask API backend, Express.js web server, and n8n workflow automation orchestrating the entire process. The modern, high-tech UI displays news in an intuitive feed format, with dedicated sections for video ideas, workflow rationale, and n8n dashboard integration.

What sets this apart is the end-to-end automation: from news discovery to video concept delivery, everything runs without manual intervention. The system is production-ready, with Nginx reverse proxy, SSL support, automated model downloads, and comprehensive error handling. It's designed for content creators, marketers, and AI enthusiasts who need to stay ahead of AI trends without the manual research overhead.

Built with Python, Node.js, Docker, and n8n, and fully deployed on Hostinger infrastructure, AI News Tracker demonstrates modern DevOps practices, containerization, and automated workflow orchestration at scale.

---

## Alternative Shorter Version (200 words)

**AI News Tracker** automates AI news discovery and video idea generation, solving information overload in the fast-moving AI space. The system continuously monitors RSS feeds, social media, and company announcements, then uses AI models to summarize news and generate video concepts with custom thumbnails.

Built with Python, Docker, and n8n workflows, the platform runs a fully automated pipeline every 6 hours: scraping, summarizing, idea generation, and thumbnail creation—all without manual intervention. The modern web interface displays curated news in an intuitive feed, with dedicated sections for video ideas and workflow automation.

The architecture demonstrates production-ready DevOps: Docker containers, Flask API, Express.js frontend, Nginx reverse proxy, and comprehensive automation. Hosted on Hostinger VPS, it showcases scalable containerization, workflow orchestration, and modern web development practices.

Perfect for content creators, marketers, and AI enthusiasts who need to stay ahead of trends without manual research. AI News Tracker turns news consumption into actionable content ideas automatically.

---

## Key Points to Highlight

✅ **Fully Automated** - No manual intervention needed
✅ **AI-Powered** - Uses Llama 3.2 and Leonardo AI
✅ **Production-Ready** - Docker, Nginx, SSL, error handling
✅ **Modern Stack** - Python, Node.js, Docker, n8n
✅ **Scalable Architecture** - Containerized, microservices
✅ **Hosted on Hostinger** - VPS deployment with full automation
✅ **Real-World Problem** - Solves AI news information overload
✅ **End-to-End** - From news to video ideas automatically

Here is the updated plan dropping the "Kiwi bird" character for a sleek, high-tech server corridor intro (matching your uploaded images), followed by the technical write-up you need for the submission.

### Part 1: Revised Video Intro Idea
**Visual:** A fast, first-person camera fly-through of the infinite server tunnel shown in your images. The orange and teal lights streak past like warp speed.
**Overlay Text:** *KiwiLab AI News* (Fade in center)
**Voiceover:** "Most AI news aggregators are just expensive wrappers. We built an engine."

#### **Leonardo AI Video Prompt (for the Server Tunnel)**
Use this prompt to generate the video clip based on the style of images you uploaded:

> **Prompt:**
> fast cinematic camera fly-through down an infinite futuristic server room corridor, glowing orange and cyan neon lights, high-tech data center, motion blur, 4k resolution, symmetrical perspective, cyberpunk aesthetic, digital data streams flowing in the air.

> **Motion Settings:**
> *   **Strength:** 6 or 7 (High speed)
> *   **Camera:** Zoom In / Move Forward (Essential to create the "tunnel" effect)

---

### Part 2: "How It Works" Write-up (100–300 Words)

This is drafted to hit all the judging criteria: **Automation, Creativity, Execution, and Impact.**

**Title: The Engine Behind KiwiLab AI News**

KiwiLab AI News is not just a wrapper for the OpenAI API; it is a self-contained, automated intelligence engine built on a production-grade microservices architecture.

**The Pipeline (Automation & Architecture)**
The backend is orchestrated by **n8n** workflows running in Docker. The system autonomously monitors dozens of RSS feeds, social signals, and event calendars. When new signals are detected, the system scrapes the full content and passes it through a cleaning layer to remove noise.

**The Intelligence (Local Inference)**
Unlike competitors burning cash on tokens, this solution utilizes **Llama 3.2** running locally via **Ollama** in a Docker container. This allows for zero-cost, unlimited inference. The LLM performs two critical tasks:
1.  **Summarization:** Condenses complex technical news into digestible insights.
2.  **Virality Analysis:** Analyzes the content against current SEO trends to generate pre-validated video ideas and hooks likely to perform well on social media.

**The Delivery (Impact & Execution)**
The frontend is a custom **Node.js/React** application served via **Nginx** with full **SSL** encryption. The entire stack is hosted on a **Hostinger VPS**, ensuring complete data sovereignty and scalability. It features automated error handling, guardrails against prompt injection, and runs 24/7 without manual intervention.

**(Word Count: ~185 words)**
