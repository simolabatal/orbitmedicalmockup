import { Cpu, ScanLine, ShieldCheck, UserRoundCheck } from 'lucide-react';
import ParallaxImage from '../ui/ParallaxImage';

const FEATURES = [
  {
    icon: ScanLine,
    label: 'Imagerie 3D & CFAO',
    text: 'Scanner intra-oral, Cone Beam et conception assistée pour des diagnostics millimétriques et des restaurations créées en un temps record.',
  },
  {
    icon: ShieldCheck,
    label: 'Stérilisation de classe B',
    text: 'Salle indépendante, autoclaves de classe B, sachets thermosoudés et traçabilité numérique par code-barres pour chaque patient.',
  },
  {
    icon: UserRoundCheck,
    label: 'Approche individuelle 1:1',
    text: 'Un nombre de patients volontairement limité par demi-journée. Votre praticien vous est dédié, sans attente et sans précipitation.',
  },
  {
    icon: Cpu,
    label: 'Technologies européennes',
    text: 'Équipements allemands et suisses, céramiques certifiées et laboratoires partenaires sélectionnés pour leur exigence.',
  },
];

export default function Cabinet() {
  return (
    <section id="cabinet" className="relative overflow-hidden bg-orbit-bg py-24 md:py-32">
      <div className="shell">
        <div className="grid gap-8 lg:grid-cols-[0.95fr_1.05fr] lg:items-end">
          <div data-reveal>
            <p className="eyebrow text-orbit-gray">Le cabinet · Rigueur clinique</p>
            <h2 className="mt-5 text-[clamp(2.2rem,4.6vw,4rem)] leading-[1.02]">
              Un sanctuaire de santé
              <br />
              conçu pour votre <em className="italic text-orbit-orange">sérénité.</em>
            </h2>
          </div>
          <div data-reveal data-delay="0.1" className="lg:pb-2">
            <p className="max-w-xl text-sm leading-relaxed text-orbit-gray md:text-[15px]">
              Chaque détail architectural et clinique a été pensé pour éliminer
              l’anxiété : lumière naturelle, matières chaudes, silence, et une
              organisation sans salle d’attente saturée. Ici, la précision médicale
              rime avec calme.
            </p>
            <a href="#technologie" className="link-underline mt-6 text-orbit-ink">
              Découvrir nos protocoles
            </a>
          </div>
        </div>

        <div className="mt-14 grid gap-10 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
          {/* Composition d'images */}
          <div className="relative" data-reveal>
            <div
              data-img-reveal
              className="relative aspect-[4/3] overflow-hidden rounded-2xl bg-orbit-sand/40"
            >
              <ParallaxImage
                src="https://images.unsplash.com/photo-1588776814546-1ffcf47267a5?auto=format&fit=crop&q=80&w=1400"
                alt="Plateau technique et équipements du cabinet Orbit Medical"
                className="h-full w-full"
                speed={5}
              />
              <div className="absolute inset-0 bg-gradient-to-t from-orbit-wood/45 via-transparent to-transparent" />
            </div>

            <div className="absolute -bottom-8 right-4 hidden w-52 overflow-hidden rounded-xl border-4 border-orbit-bg shadow-xl sm:block md:right-8 md:w-64">
              <img
                src="https://images.unsplash.com/photo-1629909613654-28e377c37b09?auto=format&fit=crop&q=80&w=800"
                alt="Espace d'accueil privé du cabinet"
                loading="lazy"
                className="aspect-[4/3] w-full object-cover"
              />
            </div>

            <div className="absolute -left-3 top-6 rounded-xl border border-black/10 bg-orbit-bg/95 px-4 py-3 shadow-lg backdrop-blur md:-left-6">
              <p className="text-[9px] font-bold uppercase tracking-[0.18em] text-orbit-orange">
                Autoclave certifié
              </p>
              <p className="mt-1 font-serif text-lg leading-none">Classe B · ISO 17665</p>
            </div>
          </div>

          {/* Piliers cliniques */}
          <ul className="grid gap-0 divide-y divide-black/10 border-y border-black/10">
            {FEATURES.map((feature, index) => {
              const Icon = feature.icon;
              return (
                <li
                  key={feature.label}
                  data-reveal
                  data-delay={index * 0.06}
                  className="group flex gap-4 py-5"
                >
                  <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full border border-black/10 bg-white text-orbit-orange transition-colors duration-500 group-hover:border-orbit-orange group-hover:bg-orbit-orange group-hover:text-white">
                    <Icon className="h-5 w-5" aria-hidden="true" />
                  </span>
                  <div>
                    <h3 className="text-lg font-medium tracking-tight">{feature.label}</h3>
                    <p className="mt-1.5 text-[13px] leading-relaxed text-orbit-gray">
                      {feature.text}
                    </p>
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      </div>
    </section>
  );
}
