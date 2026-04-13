import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Geist', 'system-ui', 'sans-serif'],
        mono: ['Geist Mono', 'monospace'],
      },
      colors: {
        brand: {
          DEFAULT: '#63b3ed',
          dim: '#4299e1',
          muted: 'rgba(99,179,237,0.15)',
        },
        surface: {
          DEFAULT: '#111113',
          raised: '#18181b',
          overlay: '#1c1c1e',
          border: '#27272a',
          hover: '#2a2a2e',
        },
        ink: {
          DEFAULT: '#e4e4e7',
          muted: '#a1a1aa',
          faint: '#52525b',
        },
      },
      borderRadius: {
        DEFAULT: '8px',
      },
      keyframes: {
        'fade-in': { from: { opacity: '0', transform: 'translateY(4px)' }, to: { opacity: '1', transform: 'translateY(0)' } },
        'slide-in': { from: { opacity: '0', transform: 'translateX(-8px)' }, to: { opacity: '1', transform: 'translateX(0)' } },
      },
      animation: {
        'fade-in': 'fade-in 0.2s ease-out',
        'slide-in': 'slide-in 0.2s ease-out',
      },
    },
  },
  plugins: [],
}
export default config
