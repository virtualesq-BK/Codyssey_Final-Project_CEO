import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: "#2F5BD3",
        "primary-dark": "#1F3F9E",
        "primary-light": "#EEF2FD",
        surface: "#F4F5F7",
        border: "#D9DCE1",
        "border-light": "#C4C8CF",
        text: "#1B1D21",
        "text-secondary": "#4A505B",
        "text-muted": "#5A606B",
        "text-disabled": "#8A909B",
        amber: "#B45309",
        "amber-bg": "#FFF7EB",
        "amber-border": "#F1D3A3",
        danger: "#B42318",
        "danger-bg": "#FDECEA",
      },
      fontFamily: {
        sans: ["IBM Plex Sans KR", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
