/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#165DFF',
        secondary: '#00B4D8',
        success: '#38B000',
        danger: '#FF4D4F',
        warning: '#FFA500',
        info: '#1E88E5',
        dark: '#1E293B',
        'dark-light': '#334155',
        'light-gray': '#F1F5F9',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}