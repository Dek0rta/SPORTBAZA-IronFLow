/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        /* ── LYFESTYLE palette ─────────────── */
        'acid':    '#c8ff00',   // acid yellow-green (primary CTA)
        'magenta': '#ff0075',   // hot pink (leaderboard)
        'voltage': '#ff4d00',   // electric orange-red (competitions)
        'uv':      '#9f00ff',   // deep ultraviolet (stats)
        'ice':     '#00f0e0',   // electric cyan (notifications)
        /* ── Legacy / kept for compatibility ── */
        'neon-green':  '#39ff14',
        'neon-purple': '#a855f7',
        'neon-pink':   '#ec4899',
        'slate-950':   '#0f172a',
        rank: {
          iron:   '#94a3b8',
          bronze: '#f59e0b',
          silver: '#e2e8f0',
          gold:   '#fbbf24',
          elite:  '#a855f7',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
