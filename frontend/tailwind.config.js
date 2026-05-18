/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Modernized UW Husky Purple ramp (600 ≈ official #4B2E83)
        brand: {
          50: "#f4f1fa",
          100: "#e7e0f3",
          200: "#cdbfe6",
          300: "#ad96d4",
          400: "#8a6abd",
          500: "#6c47a3",
          600: "#4B2E83", // official Husky Purple — primary action
          700: "#3d2569",
          800: "#2c1a4c",
          900: "#1d1133",
        },
        // UW gold — sparing accent only
        gold: {
          DEFAULT: "#B7A57A",
          soft: "#d8cba8",
          text: "#85754D",
        },
        good: "#1f7a4d",
        warn: "#9a6a14",
        bad: "#b3261e",
        // Warm editorial canvas / ink / hairline
        paper: "#F6F4EF",
        panel: "#FFFFFF",
        ink: "#1A1714",
        line: "#E4DFD5",
      },
      fontFamily: {
        display: ['"Archivo Variable"', "system-ui", "sans-serif"],
        sans: ['"Archivo Variable"', "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono Variable"', "ui-monospace", "monospace"],
      },
      borderRadius: { md: "0.125rem", xl: "0.125rem", "2xl": "0.125rem" },
      boxShadow: {
        soft: "0 1px 2px rgba(26,23,20,.04)",
      },
      maxWidth: { content: "1360px", prose: "68ch" },
      keyframes: {
        shimmer: { "100%": { transform: "translateX(100%)" } },
      },
      animation: { shimmer: "shimmer 1.4s infinite" },
    },
  },
  plugins: [require("@tailwindcss/forms")],
};
