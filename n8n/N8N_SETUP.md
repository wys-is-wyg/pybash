# Phase 11: n8n Workflow Configuration Guide

This guide walks you through setting up the n8n workflow for the AI News Tracker pipeline.

## Prerequisites

- Docker containers running (python-app, web-server, n8n)
- n8n accessible at `http://localhost:5678`
- Credentials configured in `.env` file:
  - `N8N_AUTH_PASSWORD` - Password for n8n basic auth
  - `N8N_BASIC_AUTH_USER` - Username (default: admin)

## Step 44: Access n8n UI

1. Open your browser and navigate to:

   ```
   http://localhost:5678
   ```

2. Login with credentials:
   - **Username:** `admin` (or value from `N8N_BASIC_AUTH_USER` in `.env`)
   - **Password:** Value from `N8N_AUTH_PASSWORD` in `.env`

### Understanding the n8n UI

Once logged in, you'll see:

- **Left Sidebar**: Navigation menu with "Workflows", "Executions", etc.
- **Main Area**: Workflow canvas (where you build/edit workflows)
- **Right Panel**: Node configuration panel (appears when you click a node)
- **Top Bar**: Save, Execute, and workflow settings buttons

When you open a workflow, the **workflow canvas** is the main editing area where nodes appear as boxes connected by lines. The **Webhook node** will be one of these boxes in the canvas.

## Step 45-47: Import Workflow (Recommended)

### Option A: Import Pre-configured Workflow

1. In n8n, click **"Workflows"** in the left sidebar
2. Click **"Import from File"** or **"Import from URL"**
3. Select the file: `n8n/workflows/ai-news-pipeline.json`
4. The workflow will be imported with all nodes pre-configured

### Option B: Manual Setup

If you prefer to create the workflow manually:

1. Click **"Workflows"** → **"Add Workflow"**
2. Name it: **"AI News Pipeline"**

#### Add Nodes in Order:

1. **Webhook Trigger**

   - Type: `Webhook`
   - Method: `POST`
   - Path: `run-pipeline`
   - Response Mode: `Using 'Respond to Webhook' Node`

2. **Scrape RSS Feeds**

   - Type: `HTTP Request`
   - Method: `GET`
   - URL: `http://python-app:5001/api/scrape`

3. **Summarize Articles**

   - Type: `HTTP Request`
   - Method: `POST`
   - URL: `http://python-app:5001/api/summarize`

4. **Generate Video Ideas**

   - Type: `HTTP Request`
   - Method: `POST`
   - URL: `http://python-app:5001/api/generate-ideas`

5. **Generate Thumbnails**

   - Type: `HTTP Request`
   - Method: `POST`
   - URL: `http://python-app:5001/api/generate-thumbnails`

6. **Refresh Feed**

   - Type: `HTTP Request`
   - Method: `POST`
   - URL: `http://python-app:5001/api/refresh`
   - Body: JSON

   ```json
   {
     "status": "completed",
     "workflow": "ai-news-pipeline",
     "timestamp": "{{ $now.toISO() }}"
   }
   ```

7. **Webhook Response**
   - Type: `Respond to Webhook`
   - Respond With: `JSON`
   - Response Body:
   ```json
   {
     "status": "success",
     "message": "Pipeline completed successfully",
     "timestamp": "{{ $now.toISO() }}",
     "workflow": "ai-news-pipeline"
   }
   ```

#### Connect Nodes:

Connect the nodes in sequence:

- Webhook → Scrape RSS Feeds
- Scrape RSS Feeds → Summarize Articles
- Summarize Articles → Generate Video Ideas
- Generate Video Ideas → Generate Thumbnails
- Generate Thumbnails → Refresh Feed
- Refresh Feed → Webhook Response

## Step 46: Configure Webhook for Manual Triggering

### Finding the Webhook Node

After importing or creating the workflow, you'll see the workflow canvas with all the nodes:

1. **In the workflow canvas** (the main editing area), you'll see a node labeled **"Webhook"** - this is the first node on the left side of the workflow
2. **Click on the Webhook node** - it will be highlighted and show its configuration panel on the right side
3. **In the node settings panel** (right side), you'll see the webhook URL displayed
4. **Note the URL format**: `http://localhost:5678/webhook/run-pipeline` (or similar)
5. For manual testing, you can also add a **Manual Trigger** node or use the webhook URL directly

**Tip:** If you don't see the Webhook node:

- Make sure you've imported the workflow or created it manually
- The Webhook node should be the leftmost node in the workflow
- If using the imported workflow, it's the first node in the chain

### Alternative: Add Manual Trigger

1. Add a **Manual Trigger** node at the beginning
2. Connect it to the **Scrape RSS Feeds** node
3. This allows you to test the workflow by clicking "Execute Workflow"

## Step 47: Save and Activate Workflow

1. Click **"Save"** in the top-right corner
2. Toggle the **"Active"** switch to enable the workflow
3. The workflow is now active and will respond to webhook triggers

## Step 48: Test Workflow

### Method 1: Manual Trigger (if added)

1. Click **"Execute Workflow"** button
2. Watch the execution progress through each node
3. Check for any errors in the execution log

### Method 2: Webhook Trigger

1. **Get the webhook URL from the Webhook node:**
   - In the workflow canvas, click on the **"Webhook"** node (first node on the left)
   - In the right panel, look for the webhook URL (it will be displayed in the node configuration)
   - Copy the URL (format: `http://localhost:5678/webhook/run-pipeline` or similar)
2. **Test with curl:**

   ```bash
   curl -X POST http://localhost:5678/webhook/run-pipeline \
     -H "Content-Type: application/json" \
     -d '{"trigger":"manual","timestamp":"2024-01-01T00:00:00Z"}'
   ```

3. Or use the webhook trigger script:
   ```bash
   bash app/scripts/webhook_trigger.sh
   ```

### Method 3: From n8n UI

1. **In the workflow canvas**, click on the **"Webhook"** node (first node on the left)
2. **In the node settings panel** (right side), look for:
   - **"Test URL"** button, or
   - **"Listen for Test Event"** button, or
   - **"Copy URL"** to get the webhook URL
3. Click the appropriate button to test or copy the URL for external testing

## Expected Workflow Execution

The workflow should execute in this order:

1. **Webhook Trigger** - Receives POST request
2. **Scrape RSS Feeds** - Fetches news from RSS feeds (GET /api/scrape)
3. **Summarize Articles** - Summarizes articles using AI (POST /api/summarize)
4. **Generate Video Ideas** - Generates video ideas from summaries (POST /api/generate-ideas)
5. **Generate Thumbnails** - Creates thumbnails via Leonardo API (POST /api/generate-thumbnails)
6. **Refresh Feed** - Merges data and updates feed.json (POST /api/refresh)
7. **Webhook Response** - Returns success status

## Troubleshooting

### Workflow Not Activating

- Check that the workflow is saved
- Verify the "Active" toggle is ON
- Check n8n logs: `docker-compose logs n8n`

### HTTP Request Failures

- Verify python-app container is running: `docker-compose ps`
- Check Python app logs: `docker-compose logs python-app`
- Verify network connectivity: Containers must be on `ai-network`
- Test endpoints directly:
  ```bash
  curl http://localhost:5001/health
  curl http://localhost:5001/api/scrape
  ```

### Webhook Not Responding

- Verify webhook URL is correct
- Check webhook is listening: Look for "Listening" status in n8n
- Test webhook URL directly with curl
- Check n8n container logs for errors

### Workflow Execution Errors

- Check each node's execution log in n8n UI
- Verify API endpoints are responding correctly
- Check Python app logs for script execution errors
- Ensure all required environment variables are set in `.env`

## Automation

Once the workflow is set up and tested, you can:

1. **Schedule with Cron**: Use the webhook trigger script in a cron job
2. **External Triggers**: Call the webhook URL from external systems
3. **n8n Schedules**: Use n8n's built-in Schedule Trigger node for automated runs

## Next Steps

After successful workflow setup:

- **Phase 12**: Set up cron automation for scheduled pipeline runs
- Monitor workflow executions in n8n dashboard
- Check feed.json output after successful runs
- Verify web UI displays updated content

## Additional Resources

- n8n Documentation: https://docs.n8n.io/
- n8n Community: https://community.n8n.io/
- Workflow JSON file: `n8n/workflows/ai-news-pipeline.json`
