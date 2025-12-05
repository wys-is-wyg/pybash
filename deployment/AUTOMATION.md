# Phase 12: Cron and Automation Setup Guide

This guide covers setting up automated execution of the AI News Tracker pipeline using either cron jobs or systemd timers.

## Overview

The pipeline can be automated using two methods:

1. **n8n Webhook Trigger** (Recommended) - Triggers the n8n workflow which orchestrates the pipeline
2. **Direct Pipeline Execution** - Runs Python scripts directly, bypassing n8n

## Prerequisites

- Docker containers running (python-app, web-server, n8n)
- n8n workflow configured and active (for webhook method)
- Scripts are executable: `chmod +x app/scripts/*.sh`
- `.env` file configured with required API keys

## Method 1: Cron Jobs (Recommended for Simplicity)

Cron is the traditional Unix/Linux scheduler. It's simple, widely available, and perfect for scheduled tasks.

### Quick Setup

Use the automated setup script:

```bash
bash deployment/cron-setup.sh
```

The script will:
- Guide you through script selection (webhook vs direct)
- Let you choose a schedule (every 6 hours, 12 hours, daily, or custom)
- Add the cron job automatically
- Show you the current crontab

### Manual Setup

#### Step 1: Choose Your Script

**Option A: n8n Webhook Trigger (Recommended)**
```bash
# Triggers n8n workflow via webhook
/path/to/projects/pybash/app/scripts/webhook_trigger.sh
```

**Option B: Direct Pipeline Execution**
```bash
# Runs pipeline scripts directly
/path/to/projects/pybash/app/scripts/run_pipeline.sh
```

#### Step 2: Edit Crontab

```bash
crontab -e
```

#### Step 3: Add Cron Job

**For n8n Webhook (every 6 hours):**
```bash
0 */6 * * * /home/username/projects/pybash/app/scripts/webhook_trigger.sh cron >> /home/username/projects/pybash/app/logs/cron.log 2>&1
```

**For Direct Pipeline (every 6 hours):**
```bash
0 */6 * * * /home/username/projects/pybash/app/scripts/run_pipeline.sh >> /home/username/projects/pybash/app/logs/cron.log 2>&1
```

### Common Cron Schedules

| Schedule | Cron Expression | Description |
|----------|----------------|-------------|
| Every 6 hours | `0 */6 * * *` | At minute 0 of every 6th hour |
| Every 12 hours | `0 */12 * * *` | At minute 0 of every 12th hour |
| Daily at midnight | `0 0 * * *` | At 00:00 every day |
| Daily at 6 AM | `0 6 * * *` | At 06:00 every day |
| Every 4 hours | `0 */4 * * *` | At minute 0 of every 4th hour |

### Cron Job Management

```bash
# View current crontab
crontab -l

# Edit crontab
crontab -e

# Remove all cron jobs (be careful!)
crontab -r

# View cron logs (system-dependent)
grep CRON /var/log/syslog
# or
journalctl -u cron
```

### Verifying Cron Jobs

1. **Check crontab:**
   ```bash
   crontab -l
   ```

2. **Check logs:**
   ```bash
   tail -f /home/username/projects/pybash/app/logs/cron.log
   ```

3. **Test manually:**
   ```bash
   bash app/scripts/webhook_trigger.sh cron
   ```

## Method 2: Systemd Timers (Advanced)

Systemd timers provide more features than cron, including:
- Better logging integration
- Dependencies and service management
- More flexible scheduling
- Persistent timers (catch up if system was off)

### Quick Setup

```bash
sudo bash deployment/systemd/install-systemd.sh
```

The script will:
- Install service and timer units
- Configure paths for your user
- Enable and start the timer
- Show status and useful commands

### Manual Setup

#### Step 1: Create Service File

Copy `deployment/systemd/ai-news-tracker.service` to `/etc/systemd/system/`:

```bash
sudo cp deployment/systemd/ai-news-tracker.service /etc/systemd/system/
```

Edit the file and update:
- `User=` - Your username
- `WorkingDirectory=` - Path to project
- `EnvironmentFile=` - Path to `.env` file
- `ExecStart=` - Path to script

#### Step 2: Create Timer File

Copy `deployment/systemd/ai-news-tracker.timer` to `/etc/systemd/system/`:

```bash
sudo cp deployment/systemd/ai-news-tracker.timer /etc/systemd/system/
```

Edit `OnCalendar` to change schedule:
- Every 6 hours: `OnCalendar=*-*-* 00/6:00:00`
- Every 12 hours: `OnCalendar=*-*-* 00/12:00:00`
- Daily at midnight: `OnCalendar=*-*-* 00:00:00`

#### Step 3: Install and Start

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable timer (starts on boot)
sudo systemctl enable ai-news-tracker.timer

# Start timer
sudo systemctl start ai-news-tracker.timer
```

### Systemd Timer Management

```bash
# Check timer status
sudo systemctl status ai-news-tracker.timer

# Check service status (last run)
sudo systemctl status ai-news-tracker.service

# List all timers
sudo systemctl list-timers

# View service logs
sudo journalctl -u ai-news-tracker.service -f

# Stop timer
sudo systemctl stop ai-news-tracker.timer

# Disable timer (won't start on boot)
sudo systemctl disable ai-news-tracker.timer

# Manually trigger service (test)
sudo systemctl start ai-news-tracker.service
```

## Comparison: Cron vs Systemd

| Feature | Cron | Systemd Timer |
|---------|-----|--------------|
| Simplicity | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Logging | Basic | Advanced (journald) |
| Dependencies | No | Yes |
| Persistent | No | Yes (optional) |
| Boot-time catch-up | No | Yes |
| Resource limits | No | Yes |
| User-friendly | Yes | Moderate |

**Recommendation:** Use cron for simplicity, systemd for advanced features.

## Troubleshooting

### Cron Jobs Not Running

1. **Check cron service:**
   ```bash
   sudo systemctl status cron
   # or
   sudo systemctl status crond
   ```

2. **Check cron logs:**
   ```bash
   grep CRON /var/log/syslog
   ```

3. **Verify script permissions:**
   ```bash
   ls -l app/scripts/*.sh
   chmod +x app/scripts/*.sh
   ```

4. **Test script manually:**
   ```bash
   bash app/scripts/webhook_trigger.sh cron
   ```

5. **Check environment variables:**
   - Cron runs with minimal environment
   - Ensure scripts source `.env` file
   - Use absolute paths in cron jobs

### Systemd Timer Not Running

1. **Check timer status:**
   ```bash
   sudo systemctl status ai-news-tracker.timer
   ```

2. **Check service logs:**
   ```bash
   sudo journalctl -u ai-news-tracker.service -n 50
   ```

3. **Verify paths in service file:**
   ```bash
   sudo cat /etc/systemd/system/ai-news-tracker.service
   ```

4. **Test service manually:**
   ```bash
   sudo systemctl start ai-news-tracker.service
   sudo systemctl status ai-news-tracker.service
   ```

### Webhook Trigger Failing

1. **Check n8n workflow is active:**
   - Open n8n dashboard
   - Verify workflow toggle is ON

2. **Test webhook URL:**
   ```bash
   curl -X POST http://localhost:5678/webhook/run-pipeline \
     -H "Content-Type: application/json" \
     -d '{"trigger":"test"}'
   ```

3. **Check webhook logs:**
   ```bash
   tail -f app/logs/webhook_trigger_*.log
   ```

4. **Verify N8N_WEBHOOK_URL in .env:**
   ```bash
   grep N8N_WEBHOOK_URL .env
   ```

## Best Practices

1. **Use n8n Webhook Method:**
   - Better error handling
   - Visual workflow monitoring
   - Easier debugging

2. **Log Everything:**
   - All scripts log to `app/logs/`
   - Cron/systemd capture stdout/stderr
   - Monitor logs regularly

3. **Test Before Scheduling:**
   - Run scripts manually first
   - Verify they complete successfully
   - Check logs for errors

4. **Set Appropriate Schedules:**
   - Don't run too frequently (API rate limits)
   - Consider timezone for daily runs
   - Account for processing time

5. **Monitor Execution:**
   - Set up log rotation
   - Monitor disk space
   - Check n8n dashboard for failures

## Next Steps

After setting up automation:

- **Phase 13-14**: Prepare for VPS deployment
- Monitor first few automated runs
- Adjust schedule as needed
- Set up log rotation
- Configure alerts for failures

