/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: [
    "./pages/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./app/**/*.{ts,tsx}",
    "./src/**/*.{ts,tsx}",
  ],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: { "2xl": "1400px" },
    },
    extend: {
      colors: {
        // shadcn compat
        border:      "hsl(var(--border))",
        input:       "hsl(var(--input))",
        ring:        "hsl(var(--ring))",
        background:  "hsl(var(--background))",
        foreground:  "hsl(var(--foreground))",
        primary: {
          DEFAULT:    "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT:    "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT:    "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT:    "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT:    "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT:    "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT:    "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },

        // CarbonLens Ecological Precision palette
        canvas:   "#f5f8f5",
        mint:     "#e8f2e8",
        "mint-border": "#d1e3d1",
        "sage-soft": "#eef5ee",
        forest:   "#2d7a4f",
        "forest-dark": "#1f5e3a",
        "forest-light": "#3a9a65",
        "forest-bg": "#0d1a0f",
        "forest-elevated": "#152218",
        scope1:   "#ef4444",
        scope2:   "#f97316",
        scope3:   "#eab308",

        // Ink
        ink:      "#0d1f10",
        "ink-body": "#2d3d2d",
        "ink-muted": "#5a6b5a",
        "ink-faint": "#8a9b8a",
        "on-dark":  "#e8f2e8",
        "on-dark-soft": "#8ea58e",
      },

      borderRadius: {
        lg:     "var(--radius)",
        md:     "calc(var(--radius) - 2px)",
        sm:     "calc(var(--radius) - 4px)",
        xl:     "20px",
        "2xl":  "24px",
        "3xl":  "28px",
        pill:   "9999px",
      },

      fontFamily: {
        sans:    ["Inter", "system-ui", "sans-serif"],
        display: ["Playfair Display", "Georgia", "serif"],
      },

      boxShadow: {
        card:     "0 2px 8px rgba(13,26,15,0.04)",
        "card-hover": "0 4px 16px rgba(13,26,15,0.08)",
        "forest-glow": "0 0 0 3px rgba(45,122,79,0.15)",
      },

      keyframes: {
        "accordion-down": {
          from: { height: 0 },
          to:   { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to:   { height: 0 },
        },
        fadeInUp: {
          from: { opacity: 0, transform: "translateY(10px)" },
          to:   { opacity: 1, transform: "translateY(0)" },
        },
        shimmer: {
          "0%":   { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },

      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up":   "accordion-up 0.2s ease-out",
        "fade-in-up":     "fadeInUp 0.35s cubic-bezier(0.16,1,0.3,1) both",
      },
    },
  },
  plugins: [],
};
