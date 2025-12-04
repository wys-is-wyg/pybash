/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./web/public/**/*.{html,js}",
    "./web/src/**/*.{html,js}"
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#ff6b35',
          hover: '#ff8555',
        },
        background: '#0f1419',
        surface: '#1a1f2e',
        'surface-elevated': '#252b3b',
        border: 'rgba(255, 255, 255, 0.1)',
        'text-primary': '#fff',
        'text-secondary': '#a0a8b8',
        'gradient-start': '#ff6b35',
        'gradient-end': '#ffa07a',
      },
      fontFamily: {
        sans: [
          '-apple-system',
          'BlinkMacSystemFont',
          'Segoe UI',
          'Roboto',
          'Oxygen',
          'Ubuntu',
          'Cantarell',
          'Fira Sans',
          'Droid Sans',
          'Helvetica Neue',
          'sans-serif',
        ],
      },
      backdropBlur: {
        xs: '2px',
      },
      transitionDuration: {
        '300': '300ms',
        '500': '500ms',
      },
    },
  },
  plugins: [],
}

