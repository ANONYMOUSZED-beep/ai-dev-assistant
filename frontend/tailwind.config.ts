import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./hooks/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Light "RIVR" palette (navy ink on soft grays), mapped onto the
        // existing `ide-*` token names so the whole app re-themes at once and
        // stays visually consistent with the landing page.
        ide: {
          bg: "#eef0f2", // app background (center column)
          panel: "#ffffff", // sidebars / panels
          elevated: "#f4f5f7", // cards / inline code
          hover: "#e7eaee", // hover states
          border: "#dbdfe6", // subtle navy-tinted outlines
          accent: "#24406e", // navy — text, icons, active borders
          accentMuted: "#1e325a", // deep navy — primary button background
          text: "#1e325a", // navy ink (on-surface)
          muted: "#5e6470", // secondary text
          success: "#1a7f4b",
          danger: "#c0392b",
          warning: "#b0691b",
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
