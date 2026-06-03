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
        // Severity tokens reference CSS variables declared in
        // frontend/src/index.css so they switch with theme. The
        // `rgb(var(--x) / <alpha-value>)` form keeps Tailwind opacity
        // modifiers (text-good/40, bg-warn/10, etc.) working in both
        // light and dark.
        good: "rgb(var(--good) / <alpha-value>)",
        warn: "rgb(var(--warn) / <alpha-value>)",
        bad:  "rgb(var(--bad) / <alpha-value>)",
        // Warm editorial canvas / ink / hairline
        paper: "#F6F4EF",
        panel: "#FFFFFF",
        ink: "#1A1714",
        line: "#E4DFD5",
      },
      fontFamily: {
        display: ['"Archivo Black"', "system-ui", "sans-serif"],
        sans: ['"Archivo Variable"', "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono Variable"', "ui-monospace", "monospace"],
      },
      borderRadius: { md: "0.5rem", lg: "0.75rem", xl: "1rem", "2xl": "1.25rem" },
      boxShadow: {
        soft: "0 1px 2px rgba(26,23,20,.03), 0 6px 24px -8px rgba(75,46,131,.12)",
        glow: "0 24px 70px -30px rgba(75,46,131,.45)",
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
