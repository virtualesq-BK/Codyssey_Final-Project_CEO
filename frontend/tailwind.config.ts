import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontSize: {
        xs: ["13px", { lineHeight: "20px" }],
        sm: ["15px", { lineHeight: "24px" }],
        base: ["16px", { lineHeight: "26px" }],
      },
      borderRadius: {
        lg: "12px",
        xl: "14px",
        "2xl": "16px",
      },
      colors: {
        primary: "#134CD8",
        "primary-dark": "#0F3DB0",
        "primary-light": "#EAF0FD",
        accent: "#FFB91B",
        "accent-bg": "#FFF6DE",
        surface: "#F5F7FB",
        border: "#D7E0ED",
        "border-light": "#D9DBDA",
        text: "#071B45",
        "text-secondary": "#53647A",
        "text-muted": "#53647A",
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
        // 가이드 콘셉트 B: Pretendard 하나로 (실패 시 한국어 시스템 서체)
        sans: ["Pretendard", "Noto Sans KR", "Apple SD Gothic Neo", "Malgun Gothic", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
