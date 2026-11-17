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
        civic: {
          50: "#f0f7ff",
          100: "#e0effe",
          200: "#bae0fd",
          300: "#7cc5fb",
          400: "#36a5f7",
          500: "#0c87eb",
          600: "#006bc9",
          700: "#0156a3",
          800: "#054986",
          900: "#0a3d6f",
          950: "#06264a",
        },
        panchayat: {
          50: "#f3faf6",
          100: "#e3f5eb",
          200: "#c7ebd7",
          300: "#9cd9ba",
          400: "#69be97",
          500: "#41a37a",
          600: "#308462",
          700: "#286a50",
          800: "#235441",
          900: "#1e4637",
        },
      },
      fontFamily: {
        sans: [
          "Inter",
          "-apple-system",
          "BlinkMacSystemFont",
          "'Segoe UI'",
          "Roboto",
          "'Noto Sans Kannada'",
          "'Noto Sans Devanagari'",
          "sans-serif",
        ],
      },
      minHeight: {
        touch: "44px",
      },
      minWidth: {
        touch: "44px",
      },
    },
  },
  plugins: [],
};
export default config;
