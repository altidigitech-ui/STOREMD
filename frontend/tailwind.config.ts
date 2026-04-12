import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./src/app/**/*.{ts,tsx}",
    "./src/components/**/*.{ts,tsx}",
    "./src/lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          "Inter",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
        mono: ["JetBrains Mono", "Fira Code", "Consolas", "monospace"],
      },
      colors: {
        storemd: {
          primary: "#2563eb",
          "primary-hover": "#1d4ed8",
        },
        score: {
          excellent: "#16a34a",
          good: "#65a30d",
          warning: "#ca8a04",
          poor: "#ea580c",
          critical: "#dc2626",
        },
        severity: {
          critical: "#dc2626",
          major: "#ea580c",
          minor: "#ca8a04",
          info: "#2563eb",
        },
        status: {
          success: "#16a34a",
          warning: "#ca8a04",
          error: "#dc2626",
          pending: "#6b7280",
        },
      },
    },
  },
  plugins: [],
};

export default config;
