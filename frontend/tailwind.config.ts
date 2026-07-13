import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./hooks/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // "RIVR" palette mapped onto `ide-*` tokens via CSS variables (RGB channel
        // triplets) so the whole workspace re-themes at once AND Tailwind opacity
        // modifiers (e.g. bg-ide-accent/10) keep working. Light values live in
        // :root; dark overrides live under `.dark` (see globals.css).
        ide: {
          bg: "rgb(var(--c-bg) / <alpha-value>)",
          panel: "rgb(var(--c-panel) / <alpha-value>)",
          elevated: "rgb(var(--c-elevated) / <alpha-value>)",
          hover: "rgb(var(--c-hover) / <alpha-value>)",
          border: "rgb(var(--c-border) / <alpha-value>)",
          accent: "rgb(var(--c-accent) / <alpha-value>)",
          accentMuted: "rgb(var(--c-accent-muted) / <alpha-value>)",
          text: "rgb(var(--c-text) / <alpha-value>)",
          muted: "rgb(var(--c-muted) / <alpha-value>)",
          success: "rgb(var(--c-success) / <alpha-value>)",
          danger: "rgb(var(--c-danger) / <alpha-value>)",
          warning: "rgb(var(--c-warning) / <alpha-value>)",
        },
        // Fluid accent ramp used by the landing page (gradients, glows, glass).
        fluid: {
          indigo: "#373cf0",
          violet: "#8b5cf6",
          cyan: "#5ad4ee",
          glass: "rgba(255,255,255,0.04)",
        },
      },
      backgroundImage: {
        "fluid-gradient":
          "linear-gradient(110deg, #5ad4ee 0%, #8b5cf6 45%, #373cf0 100%)",
      },
      fontFamily: {
        sans: [
          "Inter",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
        mono: [
          "JetBrains Mono",
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Consolas",
          "monospace",
        ],
      },
    },
  },
  plugins: [],
};

export default config;
