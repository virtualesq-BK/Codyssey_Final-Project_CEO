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
        primary: "#6161FF",
        "primary-dark": "#4B4BD9",
        "primary-light": "#E7ECFF",
        surface: "#F5F6F8",
        border: "#DDDFEB",
        "border-light": "#CACBCD",
        text: "#333333",
        "text-secondary": "#535768",
        "text-muted": "#535768",
        "text-disabled": "#808080",
        amber: "#B45309",
        "amber-bg": "#FFF7EB",
        "amber-border": "#F1D3A3",
        danger: "#B42318",
        "danger-bg": "#FDECEA",
      },
      // 카드용 옅은 라벤더 그림자 (레퍼런스: 무거운 그림자 금지)
      boxShadow: {
        card: "0 2px 48px rgba(205, 208, 223, 0.4)",
        "card-hover": "0 5px 45px rgba(0, 0, 0, 0.12)",
      },
      fontFamily: {
        // 영문·숫자는 Poppins, 한글은 IBM Plex Sans KR로 자동 대체
        sans: ["Poppins", "IBM Plex Sans KR", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
