import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
    "./store/**/*.{js,ts,jsx,tsx,mdx}"
  ],
  theme: {
    extend: {
      colors: {
        ink: "#22312c",
        moss: "#4f6f64",
        tide: "#206d68",
        clay: "#b65f45",
        flax: "#f6f3ea",
        cloud: "#f5f7f6",
        periwinkle: "#536a9f"
      },
      boxShadow: {
        panel: "0 18px 45px rgba(34, 49, 44, 0.10)"
      }
    }
  },
  plugins: []
};

export default config;
