import type { Config } from 'tailwindcss';

/**
 * Tailwind theme — dark-first industrial palette inspired by Satisfactory's
 * FICSIT aesthetic (dark steel surfaces, safety-orange accents).
 */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        surface: {
          DEFAULT: '#14171c',
          raised: '#1c2027',
          overlay: '#252a33',
          border: '#323945',
        },
        accent: {
          DEFAULT: '#fa9549',
          hover: '#fbaa6e',
          muted: '#8a5a35',
        },
        status: {
          ok: '#4ade80',
          warn: '#facc15',
          error: '#f87171',
          idle: '#94a3b8',
        },
      },
      fontFamily: {
        sans: ['"Inter"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
    },
  },
  plugins: [],
} satisfies Config;
