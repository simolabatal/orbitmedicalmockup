/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './core/templates/**/*.html',
    './marketplace/templates/**/*.html',
    '../apps/**/templates/**/*.html',
    './iot/templates/**/*.html',
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  '#f0f7f3',
          100: '#d4ece0',
          200: '#a9d9c1',
          300: '#7ec6a2',
          400: '#53b383',
          500: '#1A4D2E',
          600: '#153e25',
          700: '#102f1c',
          800: '#0b2013',
          900: '#06110a',
        },
        accent: {
          400: '#a3c4b4',
          500: '#1A4D2E',
          600: '#133a22',
        },
        lf: {
          dark:   '#1b4332',
          green:  '#2d6a4f',
          light:  '#40916c',
          accent: '#95d5b2',
          bg:     '#f0fdf4',
        },
        forest: {
          50:  '#f0fdf4',
          100: '#dcfce7',
          200: '#bbf7d0',
          300: '#86efac',
          400: '#34d399',
          500: '#10b981',
          600: '#059669',
          700: '#047857',
          800: '#065f46',
          900: '#064e3b',
        },
        ink: {
          DEFAULT: '#2D3436',
          soft:    '#636e72',
          muted:   '#b2bec3',
          light:   '#dfe6e9',
        },
        surface: {
          DEFAULT: '#F8F9FA',
          warm:    '#f1f3f5',
          cool:    '#edf2f4',
        },
        neutralDark: '#2D3436',
        premiumBg:   '#F8F9FA',
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        'xl':  '12px',
        '2xl': '16px',
        '3xl': '20px',
        '4xl': '24px',
      },
      boxShadow: {
        'glass':       '0 8px 32px rgba(26, 77, 46, 0.08)',
        'glass-hover': '0 12px 40px rgba(26, 77, 46, 0.14)',
      },
    },
  },
  plugins: [],
}
