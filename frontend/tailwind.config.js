/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Military HUD palette — high contrast on near-black backgrounds
        hud: {
          bg:        "#05080c",   // deepest background
          panel:     "#0a1018",   // panel bg
          panelEdge: "#1a2430",   // panel border
          grid:      "#0f1a26",   // background grid lines
          text:      "#c8d4e0",   // primary text
          textDim:   "#5a6878",   // secondary text
          accent:    "#00ffd1",   // primary cyan accent (selections, primary buttons)
          accentDim: "#00b894",   // subdued cyan
          warn:      "#ff8c42",   // amber for secondary highlights
          danger:    "#ff3860",   // red for warnings / outliers
          ok:        "#3edd6e",   // green for success / confirmed
        },
      },
      fontFamily: {
        // monospace stack — JetBrains Mono if available, fallback to system mono
        mono: ['"JetBrains Mono"', '"Fira Code"', "ui-monospace", "monospace"],
        sans: ['"Inter"', "system-ui", "sans-serif"],
      },
      boxShadow: {
        // glow effects for highlighted elements
        glow:     "0 0 12px rgba(0, 255, 209, 0.4), inset 0 0 1px rgba(0, 255, 209, 0.6)",
        glowWarn: "0 0 12px rgba(255, 140, 66, 0.4), inset 0 0 1px rgba(255, 140, 66, 0.6)",
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "scan":       "scan 4s linear infinite",
      },
      keyframes: {
        scan: {
          "0%":   { transform: "translateY(-100%)" },
          "100%": { transform: "translateY(100%)" },
        },
      },
    },
  },
  plugins: [],
};