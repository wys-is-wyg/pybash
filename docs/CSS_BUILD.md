# CSS Build Guide

This project uses **Tailwind CSS v4** for styling. The CSS is built from a source file into the public directory.

## Source and Output Files

- **Source**: `web/src/input.css` (Tailwind imports + custom CSS)
- **Output**: `web/public/css/style.css` (compiled CSS)

## Build Commands

### Option 1: Build CSS in Docker Container (Recommended)

Since Tailwind is a dev dependency, you need to install dev dependencies first:

```bash
# Install dev dependencies (includes Tailwind)
docker exec ai-news-web npm install --include=dev

# Build CSS
docker exec ai-news-web npm run build:css
```

Or as a one-liner:
```bash
docker exec ai-news-web sh -c "npm install --include=dev && npm run build:css"
```

### Option 2: Build CSS Locally (WSL)

If you have Node.js installed in WSL:

```bash
# In WSL bash (not PowerShell)
cd ~/projects/pybash/web
npm install  # Only needed first time
npm run build:css
```

**Note**: Make sure you're in WSL bash, not Windows PowerShell, when running npm commands.

### Option 3: Watch Mode (Development)

For automatic rebuilding when you edit CSS:

**Locally:**
```bash
cd web
npm run watch:css
```

**In Docker:**
```bash
docker exec -it ai-news-web npm run watch:css
```

This will watch `src/input.css` and automatically rebuild when you save changes.

## After Building

After rebuilding CSS:

1. **Hard refresh your browser** (Ctrl+Shift+R) to see changes
2. **No container restart needed** - CSS is served as static files

## Troubleshooting

### "tailwindcss: command not found"

Install dependencies first:
```bash
cd web
npm install
```

### Changes not showing?

1. Hard refresh browser (Ctrl+Shift+R)
2. Clear browser cache
3. Check that `public/css/style.css` was updated (check file timestamp)

### Need to rebuild after editing `src/input.css`?

Yes! Always run `npm run build:css` after editing the source file.

## Quick Reference

```bash
# Build once
npm run build:css

# Watch for changes (auto-rebuild)
npm run watch:css

# In Docker
docker exec ai-news-web npm run build:css
```

