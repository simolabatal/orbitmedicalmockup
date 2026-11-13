# Orbit Medical — Marrakech, Guéliz

Site vitrine haut de gamme pour le cabinet médical & dentaire **Orbit Medical** (Guéliz, Marrakech), avec prise de rendez-vous en ligne en 2 étapes et export calendrier.

## Stack

- **React 19** + **Vite 8**
- **Tailwind CSS 4** (`@tailwindcss/postcss`)
- **Lenis** (smooth scroll) + **GSAP** (animations au scroll)
- **Lucide React** (icônes) + **canvas-confetti** (confirmation de RDV)

## Démarrage

```bash
npm install
npm run dev      # http://localhost:3000
```

## Build & production

```bash
npm run build    # génère /dist
npm run preview  # prévisualise le build
```

## Déploiement Vercel

Le projet est détecté automatiquement par Vercel :

- **Framework preset** : Vite
- **Build command** : `npm run build`
- **Output directory** : `dist`

## Fonctionnalités

- Navigation par ancres fluides + menu mobile
- Modale de réservation en 2 étapes puis confirmation avec code unique `ORB-MED-XXXX`
- Export **Google Calendar** (URL) et **.ics** (Apple / Android), aligné sur le créneau choisi (fuseau `Africa/Casablanca`)
- Bouton WhatsApp sticky
- Filtres de soins + FAQ accordéon
- Animations d'apparition au scroll, respect de `prefers-reduced-motion` à prévoir si besoin
