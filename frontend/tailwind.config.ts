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
        primary: "#134CD8",
        "primary-dark": "#0F3DB0",
        "primary-light": "#EAF0FD",
        surface: "#F3F4F6",
        border: "#E5E7EB",
        "border-light": "#D9DBDA",
        text: "#111111",
        "text-secondary": "#4B5563",
        "text-muted": "#4B5563",
        "text-disabled": "#6B7280",
        amber: "#B45309",
        "amber-bg": "#FFF7EB",
        "amber-border": "#F1D3A3",
        danger: "#B42318",
        "danger-bg": "#FDECEA",
      },
      // 레퍼런스(Lottielab): 그림자 대신 1px 테두리와 바탕색 단계로 층을 나눈다
      boxShadow: {
        card: "none",
        "card-hover": "none",
      },
      fontFamily: {
        // 영문·숫자는 Plus Jakarta Sans, 한글은 IBM Plex Sans KR로 자동 대체
        sans: ["Plus Jakarta Sans", "IBM Plex Sans KR", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
