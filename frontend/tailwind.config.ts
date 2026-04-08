import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}"
  ],
  theme: {
    extend: {
      colors: {
        ink: "#161616",
        paper: "#f8f4ec",
        saffron: "#b5522a",
        forest: "#203b33",
        sand: "#dcc7a1"
      },
      fontFamily: {
        sans: ["var(--font-sans)"],
        display: ["var(--font-display)"]
      },
      boxShadow: {
        card: "0 18px 60px rgba(26, 22, 16, 0.12)"
      }
    }
  },
  plugins: []
};

export default config;
