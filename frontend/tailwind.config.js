/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      // Colors live in tokens.js (inline styles) — no brand-* needed here.
      // Font families are defined for reference; components use tokens.js F.display etc.
      fontFamily: {
        display: ["'Space Grotesk'", 'system-ui', 'sans-serif'],
        mono:    ["'JetBrains Mono'", 'monospace'],
      },
    },
  },
  plugins: [],
};
