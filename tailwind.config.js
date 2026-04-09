/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ["Sora", "Segoe UI", "sans-serif"],
        body: ["Manrope", "Segoe UI", "sans-serif"],
      },
      colors: {
        brand: {
          50: "#fff6eb",
          100: "#ffe9cc",
          200: "#ffd29b",
          300: "#ffb767",
          400: "#ff9d3f",
          500: "#f17f1a",
          600: "#cf6511",
          700: "#aa4f0f",
          800: "#883f12",
          900: "#703613",
        },
      },
      boxShadow: {
        panel: "0 12px 26px -16px rgba(40, 22, 6, 0.36)",
      },
    },
  },
  plugins: [],
};
