/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        clinical: {
          bg: '#f8fafc',
          panel: '#ffffff',
          border: '#e2e8f0',
          text: '#0f172a',
          'text-dim': '#475569',
          accent: '#2563eb',
          success: '#166534',
          warning: '#92400e',
          error: '#991b1b',
        }
      },
      fontFamily: {
        sans: ['system-ui', 'Arial', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
