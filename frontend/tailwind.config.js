/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        base: "#090A0F",
        panel: "#11131A",
        panel2: "#161924",
        line: "#1E2230",
        ink: { DEFAULT: "#E6E8EE", dim: "#9AA0AE", faint: "#5D6474" },
        gain: "#10B981",
        loss: "#EF4444",
        warn: "#F59E0B",
        accent: "#6E8BFF",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["'JetBrains Mono'", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
