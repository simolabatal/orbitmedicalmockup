import { ArrowUpRight, ShieldCheck } from 'lucide-react';
import ParallaxImage from '../ui/ParallaxImage';

const PROTOCOL = [
  {
    number: '01',
    title: 'Décontamination immédiate',
    text: 'Bain à ultrasons et désinfection de chaque instrument dès la fin de l’intervention.',
  },
  {
    number: '02',
    title: 'Conditionnement tracé',
    text: 'Double sachet thermosoudé, témoin de stérilisation et code-barres nominatif.',
  },
  {
    number: '03',
    title: 'Autoclave de classe B',
    text: 'Fractionnement de vide poussé, cycle validé et contrôle biologique hebdomadaire.',
  },
  {
    number: '04',
    title: 'Traçabilité numérique',
    text: 'Chaque soin est relié à son cycle de stérilisation, archivé et consultable.',
  },
];

export default function Technology() {
  return (
    <section
      id="technologie"
      className="relative overflow-hidden bg-orbit-wood py-24 text-orbit-bg md:py-32"
    >
      <div className="dot-grid-light pointer-events-none absolute inset-0 opacity-30" aria-hidden="true" />
      <div
        className="pointer-events-none absolute -left-32 top-1/4 h-96 w-96 rounded-full border border-white/10"
        aria-hidden="true"
      />
      <div
        className="pointer-events-none absolute -left-16 top-1/3 h-48 w-48 rounded-full border border-orbit-orange/30"
        aria-hidden="true"
      />

      <div className="shell relative grid gap-14 lg:grid-cols-[1.05fr_0.95fr] lg:items-center">
        <div>
          <p className="eyebrow text-orbit-sand/80" data-reveal>
            Sécurité sanitaire absolue
          </p>
          <h2
            data-reveal
            className="mt-5 text-[clamp(2.2rem,4.6vw,4rem)] leading-[1.02]"
          >
            Le protocole de
            <br />
            stérilisation <em className="italic text-orbit-orange">classe B.</em>
          </h2>
          <p
            data-reveal
            data-delay="0.08"
            className="mt-6 max-w-xl text-sm leading-relaxed text-white/60"
          >
            Parce que votre santé n’admet aucun compromis, Orbit Medical s’est doté
            d’une centrale de stérilisation indépendante, entièrement traçable, aux
            exigences des cliniques européennes.
          </p>

          <ol className="mt-10 border-t border-white/15" data-reveal data-delay="0.12">
            {PROTOCOL.map((step) => (
              <li
                key={step.number}
                className="group grid grid-cols-[auto_1fr] gap-5 border-b border-white/15 py-5"
              >
                <span className="font-serif text-lg text-orbit-orange">{step.number}</span>
                <div>
                  <h3 className="text-base font-medium text-white">{step.title}</h3>
                  <p className="mt-1 text-xs leading-relaxed text-white/50">{step.text}</p>
                </div>
              </li>
            ))}
          </ol>

          <a href="#contact" className="link-underline mt-8 text-orbit-sand hover:text-white">
            Visiter le cabinet
            <ArrowUpRight className="h-3.5 w-3.5" aria-hidden="true" />
          </a>
        </div>

        <div className="relative" data-reveal data-delay="0.15">
          <div className="relative aspect-[4/5] overflow-hidden rounded-2xl border border-white/10 sm:aspect-[4/4.4]">
            <ParallaxImage
              src="https://images.unsplash.com/photo-1588776814546-1ffcf47267a5?auto=format&fit=crop&q=80&w=1200"
              alt="Salle de stérilisation et équipements médicaux Orbit"
              className="h-full w-full"
              speed={5}
              imgClassName="opacity-90"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-orbit-wood via-orbit-wood/10 to-transparent" />

            <div className="absolute left-5 top-5 inline-flex items-center gap-2 rounded-full border border-white/20 bg-orbit-wood/60 px-3.5 py-2 text-[9px] font-bold uppercase tracking-[0.14em] backdrop-blur">
              <ShieldCheck className="h-3.5 w-3.5 text-orbit-orange" aria-hidden="true" />
              Norme ISO · CE
            </div>
          </div>

          <div className="absolute -bottom-6 -left-4 max-w-[240px] rounded-xl border border-orbit-sand/40 bg-orbit-bg p-5 text-orbit-ink shadow-2xl sm:-left-8">
            <p className="text-[9px] font-bold uppercase tracking-[0.16em] text-orbit-orange">
              Contrôle indépendant
            </p>
            <p className="mt-2 font-serif text-lg leading-tight">
              Tests biologiques validés chaque semaine.
            </p>
            <p className="mt-2 text-[11px] leading-relaxed text-orbit-gray">
              Résultats archivés et disponibles sur demande.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
