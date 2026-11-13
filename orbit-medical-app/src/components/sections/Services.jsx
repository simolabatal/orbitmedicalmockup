import { useState } from 'react';
import { ArrowUpRight, BadgeCheck } from 'lucide-react';
import { CATEGORIES, POLES, TREATMENTS } from '../../data/clinic';

export default function Services({ onBook }) {
  const [activeCategory, setActiveCategory] = useState('Tous');

  const groups =
    activeCategory === 'Tous'
      ? CATEGORIES
      : CATEGORIES.filter((category) => category === activeCategory);

  return (
    <section id="soins" className="relative overflow-hidden bg-orbit-bg py-24 md:py-32">
      <div className="shell">
        <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
          <div data-reveal>
            <p className="eyebrow text-orbit-gray">Soins · Transparence tarifaire</p>
            <h2 className="mt-5 max-w-2xl text-[clamp(2.2rem,4.6vw,4rem)] leading-[1.02]">
              Trois pôles d’excellence.
              <br />
              Des tarifs <em className="italic text-orbit-orange">clairs.</em>
            </h2>
          </div>
          <p
            data-reveal
            data-delay="0.1"
            className="max-w-sm text-sm leading-relaxed text-orbit-gray"
          >
            Aucun frais caché. Chaque devis est remis après un bilan 3D complet, avec
            un plan de traitement détaillé et des options de financement.
          </p>
        </div>

        {/* Cartes pôles */}
        <div className="mt-12 grid gap-6 md:grid-cols-3">
          {POLES.map((pole, index) => (
            <article
              key={pole.id}
              data-reveal
              data-delay={index * 0.08}
              className="group card-lift overflow-hidden rounded-2xl border border-black/10 bg-white"
            >
              <a
                href="#grille-tarifs"
                onClick={() => setActiveCategory(pole.category)}
                className="block"
              >
                <div className="relative aspect-[4/3] overflow-hidden bg-orbit-sand/40">
                  <img
                    src={pole.image}
                    alt={`Pôle ${pole.title} — Orbit Medical`}
                    loading="lazy"
                    decoding="async"
                    className="h-full w-full object-cover transition-transform duration-[900ms] ease-[cubic-bezier(0.22,1,0.36,1)] group-hover:scale-[1.06]"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-orbit-wood/55 via-transparent to-transparent" />
                  <span className="absolute left-4 top-4 inline-flex items-center gap-2 rounded-full bg-orbit-bg/90 px-3 py-1.5 text-[9px] font-bold uppercase tracking-[0.16em] text-orbit-ink backdrop-blur">
                    <BadgeCheck className="h-3 w-3 text-orbit-orange" aria-hidden="true" />
                    {pole.range}
                  </span>
                  <span className="absolute bottom-4 right-4 font-serif text-3xl font-light text-white/85">
                    {pole.number}
                  </span>
                </div>

                <div className="p-6">
                  <div className="flex items-start justify-between gap-3">
                    <h3 className="text-xl font-medium leading-tight">{pole.title}</h3>
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-black/10 text-orbit-ink transition-all duration-500 group-hover:border-orbit-orange group-hover:bg-orbit-orange group-hover:text-white">
                      <ArrowUpRight className="h-4 w-4" aria-hidden="true" />
                    </span>
                  </div>
                  <p className="mt-3 text-[13px] leading-relaxed text-orbit-gray">
                    {pole.description}
                  </p>
                </div>
              </a>
            </article>
          ))}
        </div>

        {/* Grille tarifaire */}
        <div id="grille-tarifs" className="mt-16 scroll-mt-28 md:mt-20">
          <div className="flex flex-col gap-5 border-t border-black/10 pt-8 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-orbit-gray">
                Tarifs indicatifs · MAD
              </p>
              <p className="mt-1 font-serif text-2xl">Votre plan, sans surprise.</p>
            </div>

            <div className="flex flex-wrap gap-2" role="group" aria-label="Filtrer les soins">
              {['Tous', ...CATEGORIES].map((category) => {
                const selected = activeCategory === category;
                return (
                  <button
                    key={category}
                    type="button"
                    onClick={() => setActiveCategory(category)}
                    aria-pressed={selected}
                    className={`rounded-full border px-4 py-2 text-[10px] font-bold uppercase tracking-[0.1em] transition-colors duration-300 ${
                      selected
                        ? 'border-orbit-ink bg-orbit-ink text-orbit-bg'
                        : 'border-black/15 bg-transparent text-orbit-ink hover:border-orbit-orange hover:text-orbit-orange'
                    }`}
                  >
                    {category === 'Tous' ? 'Tous les soins' : category}
                  </button>
                );
              })}
            </div>
          </div>

          <div key={activeCategory} className="animate-fade-up mt-6">
            {groups.map((group) => {
              const treatments = TREATMENTS.filter(
                (treatment) => treatment.category === group
              );

              return (
                <div key={group} className="mb-12 last:mb-0">
                  <div className="mb-2 flex items-center justify-between border-b border-black/15 pb-3">
                    <h3 className="text-lg font-medium">{group}</h3>
                    <span className="text-[10px] font-semibold uppercase tracking-[0.16em] text-orbit-gray">
                      {treatments.length} soins
                    </span>
                  </div>

                  <ul>
                    {treatments.map((treatment) => (
                      <li
                        key={treatment.id}
                        className="group grid gap-3 border-b border-black/10 py-5 transition-colors duration-300 hover:bg-orbit-sand/15 md:grid-cols-[1fr_130px_170px_auto] md:items-center md:gap-6 md:px-3"
                      >
                        <div>
                          <div className="flex flex-wrap items-center gap-2">
                            <h4 className="font-serif text-xl leading-tight transition-colors group-hover:text-orbit-orange">
                              {treatment.name}
                            </h4>
                            {treatment.badge ? (
                              <span className="rounded-full bg-orbit-sand/60 px-2.5 py-0.5 text-[9px] font-bold uppercase tracking-[0.1em] text-orbit-wood">
                                {treatment.badge}
                              </span>
                            ) : null}
                          </div>
                          <p className="mt-1.5 max-w-xl text-xs leading-relaxed text-orbit-gray">
                            {treatment.description}
                          </p>
                        </div>

                        <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-orbit-gray">
                          {treatment.duration}
                        </p>

                        <p className="font-serif text-xl leading-none md:text-right">
                          {treatment.price}
                          <span className="mt-1 block font-sans text-[9px] font-medium uppercase tracking-[0.1em] text-orbit-gray">
                            {treatment.priceNote}
                          </span>
                        </p>

                        <button
                          type="button"
                          onClick={() => onBook(treatment)}
                          className="inline-flex items-center justify-center gap-2 justify-self-start rounded-full border border-black/15 px-4 py-2.5 text-[10px] font-bold uppercase tracking-[0.12em] transition-colors duration-300 hover:border-orbit-orange hover:bg-orbit-orange hover:text-white md:justify-self-end"
                        >
                          Réserver
                          <ArrowUpRight className="h-3.5 w-3.5" aria-hidden="true" />
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              );
            })}
          </div>

          <p className="rounded-xl border border-orbit-sand bg-orbit-sand/25 px-4 py-3 text-[11px] leading-relaxed text-orbit-gray">
            Tarifs indicatifs en dirhams marocains (MAD), susceptibles d’évoluer selon
            le diagnostic. Un devis définitif vous est remis avant tout traitement.
          </p>
        </div>
      </div>
    </section>
  );
}
