# Building CSS with Tailwind

This project uses Tailwind CSS v4 for styling. The CSS file (`public/css/style.css`) is currently a comprehensive standalone version that works immediately.

## To Build Tailwind CSS (Optional Enhancement)

1. Install dependencies:
```bash
cd web
npm install
```

2. Build CSS (one-time):
```bash
npm run build:css
```

3. Watch for changes during development:
```bash
npm run watch:css
```

The build process will:
- Read from `src/input.css` (Tailwind source)
- Generate utilities based on classes used in HTML
- Output to `public/css/style.css` (will overwrite current file)

## Current Setup

- **Current CSS**: `public/css/style.css` - Works immediately, includes all necessary styles
- **Tailwind Config**: `tailwind.config.js` - Custom theme matching Figma exemplar
- **Tailwind Source**: `src/input.css` - Source file for Tailwind build

## Design System

The design system matches the Figma exemplar:
- Primary color: `#ff6b35` (orange)
- Background: `#0f1419` (dark blue)
- Surface: `#1a1f2e` / `#252b3b` (elevated)
- Text: `#fff` / `#a0a8b8` (secondary)
- Gradient: `#ff6b35` → `#ffa07a`

All colors are defined as CSS variables in `style.css` and can be customized.

