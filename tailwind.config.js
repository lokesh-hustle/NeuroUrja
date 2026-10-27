/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        nu: {
          white: '#FFFFFF',
          slate: '#F8FAFC',
          border: '#E2E8F0',
          ink: '#0F172A',
          muted: '#475569',
          emerald: '#10B981',
          sky: '#0284C7',
          amber: '#F59E0B',
          rose: '#F43F5E',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'Segoe UI', 'sans-serif'],
      },
      boxShadow: {
        card: '0 1px 2px rgba(15, 23, 42, 0.04), 0 10px 24px rgba(15, 23, 42, 0.06)',
      },
    },
  },
  plugins: [],
}
