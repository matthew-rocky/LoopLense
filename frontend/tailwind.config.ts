import type { Config } from "tailwindcss";

export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#ecfdf5",
        panel: "rgba(15, 23, 42, 0.66)"
      },
      boxShadow: {
        glow: "0 24px 70px rgba(20, 184, 166, 0.16)"
      }
    }
  },
  plugins: []
} satisfies Config;

