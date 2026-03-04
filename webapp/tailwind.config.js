/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
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
