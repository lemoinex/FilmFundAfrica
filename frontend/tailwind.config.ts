import type { Config } from "tailwindcss";

/**
 * Palette : encre profonde (salle de projection), laiton chaud (accent),
 * bleu-gris froid (données, finance). Pas de clichés caméra/clap/pellicule.
 */
const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#0A0C10",
          900: "#0F1219",
          800: "#161A24",
          700: "#1F2531",
          600: "#2B3341",
          500: "#3C4657",
        },
        brass: {
          50: "#FBF6EC",
          100: "#F5E9D0",
          200: "#E9D2A3",
          300: "#DBB870",
          400: "#CBA04A",
          500: "#B4862F",
          600: "#8F6821",
          700: "#6B4D19",
        },
        slatey: {
          100: "#E7EBF2",
          200: "#C6CEDC",
          300: "#9BA7BC",
          400: "#73819A",
          500: "#556277",
        },
        signal: {
          success: "#4C9A6A",
          warning: "#C98A2E",
          danger: "#B4564C",
          info: "#4A7BA7",
        },
      },
      fontFamily: {
        // Les polices web sont chargées au runtime ; ces piles servent de repli
        // immédiat et restent lisibles si Google Fonts est inaccessible.
        sans: [
          "Inter",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "Helvetica Neue",
          "sans-serif",
        ],
        display: ["Fraunces", "Iowan Old Style", "Georgia", "Times New Roman", "serif"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(0,0,0,.28), 0 8px 24px -12px rgba(0,0,0,.5)",
        lift: "0 2px 4px rgba(0,0,0,.3), 0 18px 40px -18px rgba(0,0,0,.65)",
      },
      backgroundImage: {
        "grain-fade":
          "radial-gradient(ellipse 80% 55% at 50% -10%, rgba(203,160,74,.14), transparent 60%)",
      },
      keyframes: {
        "fade-up": {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          "100%": { transform: "translateX(100%)" },
        },
      },
      animation: {
        "fade-up": "fade-up .4s ease-out both",
        shimmer: "shimmer 1.6s infinite",
      },
    },
  },
  plugins: [],
};

export default config;
