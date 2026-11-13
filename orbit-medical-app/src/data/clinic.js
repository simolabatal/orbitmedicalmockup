export const CLINIC = {
  name: 'Orbit Medical',
  tagline: "L'art de la santé et du sourire.",
  city: 'Marrakech',
  district: 'Guéliz',
  address: "Centre d'Affaires Jawhara",
  street: 'Boulevard Moulay Rachid',
  postal: '40000 Marrakech, Maroc',
  phone: '+212 5 24 43 00 00',
  phoneHref: 'tel:+212524430000',
  whatsapp: '+212 6 61 00 00 00',
  whatsappHref:
    'https://wa.me/212661000000?text=Bonjour%20Orbit%20Medical%2C%20je%20souhaite%20un%20renseignement%20m%C3%A9dical.',
  email: 'contact@orbit-medical.ma',
  hours: 'Lundi – Samedi · 09h00 – 19h30',
  hoursDetail: 'Sans interruption. Urgences sur appel direct.',
  mapsUrl:
    "https://www.google.com/maps/search/?api=1&query=Centre+d'Affaires+Jawhara+Boulevard+Moulay+Rachid+Gu%C3%A9liz+Marrakech",
};

export const NAV_LINKS = [
  { href: '#accueil', label: 'Accueil' },
  { href: '#cabinet', label: 'Le Cabinet' },
  { href: '#soins', label: 'Soins & Tarifs' },
  { href: '#technologie', label: 'Stérilisation 3D' },
  { href: '#faq', label: 'FAQ' },
  { href: '#contact', label: 'Contact' },
];

export const CATEGORIES = [
  'Esthétique du sourire',
  'Implantologie avancée',
  'Soins conservateurs & Bilan',
];

export const TREATMENTS = [
  // Esthétique
  {
    id: 'facettes',
    name: 'Facettes céramique haute définition',
    category: 'Esthétique du sourire',
    duration: '2 séances · 1 semaine',
    price: '4 500 MAD',
    priceNote: 'par dent',
    description:
      'Conception numérique 3D et céramique feldspathique pressée pour un sourire naturel, lumineux et sans altération de l’émail.',
    badge: 'Signature Orbit',
  },
  {
    id: 'blanchiment',
    name: 'Blanchiment LED à froid',
    category: 'Esthétique du sourire',
    duration: '1 h 15',
    price: '2 800 MAD',
    priceNote: 'séance complète',
    description:
      'Éclaircissement médical maîtrisé, protection gingivale et gain immédiat de 3 à 8 teintes, sans sensibilité durable.',
    badge: 'Populaire',
  },
  {
    id: 'design-sourire',
    name: 'Design digital du sourire (DSD)',
    category: 'Esthétique du sourire',
    duration: '45 min',
    price: '1 200 MAD',
    priceNote: 'étude & simulation',
    description:
      'Analyse photo-vidéo, simulation esthétique et plan de traitement chiffré avant toute intervention irréversible.',
    badge: '',
  },

  // Implantologie
  {
    id: 'implant',
    name: 'Implant dentaire titane grade médical',
    category: 'Implantologie avancée',
    duration: 'Chirurgie guidée 3D',
    price: '8 500 MAD',
    priceNote: 'implant + pilier',
    description:
      'Pose mini-invasive guidée par ordinateur, implant européen tracé et garanti 10 ans, avec pilier personnalisé.',
    badge: 'Garantie 10 ans',
  },
  {
    id: 'greffe',
    name: 'Greffe osseuse & sinus lift',
    category: 'Implantologie avancée',
    duration: '1 h 30',
    price: 'Dès 4 000 MAD',
    priceNote: 'selon le volume',
    description:
      'Régénération osseuse et élévation sinusienne sous anesthésie locale, pour sécuriser les cas implantaires complexes.',
    badge: 'Expertise',
  },
  {
    id: 'couronne',
    name: 'Couronne céramique CFAO',
    category: 'Implantologie avancée',
    duration: '2 séances',
    price: '3 500 MAD',
    priceNote: 'par unité',
    description:
      'Usinage en laboratoire partenaire, ajustage millimétrique et rendu translucide identique à la dent naturelle.',
    badge: '',
  },

  // Soins
  {
    id: 'bilan',
    name: 'Bilan digital 3D & scanner intra-oral',
    category: 'Soins conservateurs & Bilan',
    duration: '45 min',
    price: '800 MAD',
    priceNote: 'diagnostic complet',
    description:
      'Examen clinique, imagerie panoramique 3D, empreinte numérique et plan de prévention personnalisé.',
    badge: 'Essentiel',
  },
  {
    id: 'detartrage',
    name: 'Détartrage & polissage aéropolisseur',
    category: 'Soins conservateurs & Bilan',
    duration: '45 min',
    price: '600 MAD',
    priceNote: 'séance',
    description:
      'Élimination douce du tartre sous-gingival par ultrasons et polissage à l’aéropolisseur pour un éclat immédiat.',
    badge: 'Douceur',
  },
  {
    id: 'soins',
    name: 'Soins conservateurs & inlays céramique',
    category: 'Soins conservateurs & Bilan',
    duration: '30 à 60 min',
    price: 'Dès 500 MAD',
    priceNote: 'selon l’acte',
    description:
      'Soins sans douleur sous loupes binoculaires, restaurations céramique collées et traitement des caries profondes.',
    badge: '',
  },
];

export const POLES = [
  {
    id: 'esthetique',
    number: '01',
    title: 'Esthétique du sourire',
    category: 'Esthétique du sourire',
    range: 'Dès 1 200 MAD',
    description:
      'Facettes, blanchiment médical et design digital : un sourire dessiné pour vous, jamais standardisé.',
    image:
      'https://images.unsplash.com/photo-1606811841689-23dfddce3e95?auto=format&fit=crop&q=80&w=1200',
  },
  {
    id: 'implantologie',
    number: '02',
    title: 'Implantologie avancée',
    category: 'Implantologie avancée',
    range: 'Dès 4 000 MAD',
    description:
      'Chirurgie guidée par ordinateur, greffes et restaurations céramique pour remplacer sans jamais dénaturer.',
    image:
      'https://images.unsplash.com/photo-1609840114035-3c981b782dfe?auto=format&fit=crop&q=80&w=1200',
  },
  {
    id: 'prevention',
    number: '03',
    title: 'Soins & Prévention',
    category: 'Soins conservateurs & Bilan',
    range: 'Dès 500 MAD',
    description:
      'Bilan 3D, détartrage et soins conservateurs : préserver la santé avant d’embellir, toujours.',
    image:
      'https://images.unsplash.com/photo-1606265752439-1f18756aa5fc?auto=format&fit=crop&q=80&w=1200',
  },
];

export const FAQS = [
  {
    q: 'Comment se déroule la première consultation VIP à Guéliz ?',
    a: 'Votre première visite comprend un accueil personnalisé sans attente, un scan intra-oral 3D complet, un entretien approfondi avec nos spécialistes et la modélisation numérique de votre futur sourire. Vous repartez avec un plan de traitement clair et chiffré.',
  },
  {
    q: 'Quelles garanties couvrent les implants et les facettes ?',
    a: 'Tous nos implants bénéficient d’une traçabilité internationale et d’une garantie décennale. Les facettes céramiques sont garanties 10 ans contre tout défaut de scellement ou de fracture, sous réserve des contrôles annuels inclus dans votre suivi.',
  },
  {
    q: 'Le cabinet accueille-t-il les patients internationaux ?',
    a: 'Absolument. Nous recevons chaque semaine une patientèle européenne et du Golfe. Notre équipe peut coordonner votre séjour à Marrakech : transferts privés, hébergement partenaire et calendrier de soins condensé sur votre disponibilité.',
  },
  {
    q: 'Quels protocoles de stérilisation appliquez-vous ?',
    a: 'Orbit Medical respecte les normes européennes les plus strictes. Nous disposons d’une salle de stérilisation indépendante, d’autoclaves de classe B, de sachets thermosoudés tracés par code-barres et de contrôles biologiques hebdomadaires validés par un laboratoire externe.',
  },
  {
    q: 'La prise de rendez-vous est-elle vraiment sans attente ?',
    a: 'Oui. Nous limitons volontairement le nombre de patients par demi-journée. Votre praticien vous est dédié en 1:1 et votre créneau inclut le temps de préparation, de soin et de conseils post-opératoires. Le retard n’est pas une option.',
  },
  {
    q: 'Comment se passe le financement des soins ?',
    a: 'Un devis détaillé vous est remis après le bilan 3D. Nous proposons un paiement en plusieurs fois sans frais sur les plans de traitement supérieurs à 10 000 MAD, ainsi que la prise en charge des assurances privées internationales.',
  },
];

export const TRUST_STATS = [
  { value: '100 %', label: 'Stérilisation de classe B' },
  { value: '1:1', label: 'Prise en charge sans attente' },
  { value: '4.9/5', label: 'Avis patients vérifiés' },
  { value: '10 ans', label: 'Garantie implantaire' },
];

export const TIME_SLOTS = [
  { value: '09:30', label: '09h30', note: 'Matin' },
  { value: '11:00', label: '11h00', note: 'Matin' },
  { value: '15:00', label: '15h00', note: 'Après-midi' },
  { value: '17:30', label: '17h30', note: 'Fin de journée' },
];

export const MARQUEE_ITEMS = [
  'Esthétique du sourire',
  'Implantologie guidée 3D',
  'Stérilisation de classe B',
  'Imagerie Cone Beam',
  'Approche 1:1 sans attente',
  'Guéliz · Marrakech',
];
