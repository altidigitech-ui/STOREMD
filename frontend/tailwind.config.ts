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
        sans: ["var(--font-jakarta)", "system-ui", "sans-serif"],
        display: ["var(--font-outfit)", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "Consolas", "monospace"],
      },
      colors: {
        storemd: {
          primary: "#2563eb",
          "primary-hover": "#1d4ed8",
        },
        ink: {
          950: "#050507",
          900: "#0a0a0f",
          800: "#0d1117",
          700: "#111827",
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
      boxShadow: {
        glow: "0 0 40px rgba(6, 182, 212, 0.35)",
        "glow-sm": "0 0 20px rgba(6, 182, 212, 0.25)",
      },
      keyframes: {
        "gradient-shift": {
          "0%, 100%": { backgroundPosition: "0% 50%" },
          "50%": { backgroundPosition: "100% 50%" },
        },
        "float-slow": {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-12px)" },
        },
        marquee: {
          "0%": { transform: "translateX(0)" },
          "100%": { transform: "translateX(-50%)" },
        },
        "pulse-ring": {
          "0%": { transform: "scale(1)", opacity: "0.5" },
          "100%": { transform: "scale(1.6)", opacity: "0" },
        },
      },
      animation: {
        "gradient-shift": "gradient-shift 18s ease infinite",
        "float-slow": "float-slow 6s ease-in-out infinite",
        marquee: "marquee 30s linear infinite",
        "pulse-ring": "pulse-ring 2.2s cubic-bezier(0.4,0,0.6,1) infinite",
      },
    },
  },
  plugins: [],
};

export default config;
