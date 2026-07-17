/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      screens: {
        // Extra-small breakpoint for phone-specific layout tweaks,
        // below Tailwind's default 'sm' (640px).
        xs: '480px',
      },
    },
  },
  plugins: [],
}
