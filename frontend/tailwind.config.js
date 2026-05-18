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
        good: "#0f9d58",
        warn: "#d08700",
        bad: "#dc2626",
        ink: "#0f1222",
      },
      fontFamily: {
        display: ['"Sora Variable"', "system-ui", "sans-serif"],
        sans: ['"Inter Variable"', "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono Variable"', "ui-monospace", "monospace"],
      },
      borderRadius: { xl: "0.875rem", "2xl": "1.25rem", "3xl": "1.75rem" },
      boxShadow: {
        soft: "0 1px 2px rgba(16,18,34,.04), 0 4px 16px rgba(16,18,34,.06)",
        lift: "0 8px 30px rgba(75,46,131,.12)",
        glow: "0 0 0 1px rgba(75,46,131,.08), 0 10px 40px rgba(75,46,131,.18)",
      },
      maxWidth: { content: "1080px" },
      keyframes: {
        shimmer: { "100%": { transform: "translateX(100%)" } },
      },
      animation: { shimmer: "shimmer 1.4s infinite" },
    },
  },
  plugins: [require("@tailwindcss/forms")],
};
