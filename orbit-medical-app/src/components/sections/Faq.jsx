import { useState } from 'react';
import { ArrowUpRight, MessageCircle, Plus } from 'lucide-react';
import { CLINIC, FAQS } from '../../data/clinic';

export default function Faq() {
  const [openIndex, setOpenIndex] = useState(0);

  return (
    <section id="faq" className="relative bg-orbit-bg py-24 md:py-32">
      <div className="shell grid gap-12 lg:grid-cols-[0.8fr_1.2fr] lg:gap-20">
        <div className="lg:sticky lg:top-28 lg:self-start" data-reveal>
          <p className="eyebrow text-orbit-gray">Prévention · Conseils</p>
          <h2 className="mt-5 text-[clamp(2.2rem,4.4vw,3.8rem)] leading-[1.02]">
            Questions
            <br />
            <em className="italic text-orbit-orange">fréquentes.</em>
          </h2>
          <p className="mt-5 max-w-sm text-sm leading-relaxed text-orbit-gray">
            Protocoles, suites opératoires, garanties : tout ce qu’il faut savoir
            avant votre première visite à Guéliz.
          </p>

          <div className="mt-8 rounded-2xl border border-orbit-sand bg-orbit-sand/25 p-5">
            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-orbit-wood">
              Une question médicale ?
            </p>
            <p className="mt-2 text-xs leading-relaxed text-orbit-gray">
              Notre équipe répond en moins de 15 minutes sur WhatsApp, pendant les
              heures d’ouverture.
            </p>
            <a
              href={CLINIC.whatsappHref}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-4 inline-flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.12em] text-orbit-ink transition-colors hover:text-orbit-orange"
            >
              <MessageCircle className="h-4 w-4" aria-hidden="true" />
              Écrire sur WhatsApp
              <ArrowUpRight className="h-3.5 w-3.5" aria-hidden="true" />
            </a>
          </div>
        </div>

        <div className="border-t border-black/15" data-reveal data-delay="0.08">
          {FAQS.map((faq, index) => {
            const isOpen = openIndex === index;
            const triggerId = `faq-trigger-${index}`;
            const panelId = `faq-panel-${index}`;

            return (
              <div key={faq.q} className="border-b border-black/15">
                <h3>
                  <button
                    id={triggerId}
                    type="button"
                    aria-expanded={isOpen}
                    aria-controls={panelId}
                    onClick={() => setOpenIndex(isOpen ? null : index)}
                    className="group flex w-full items-start justify-between gap-6 py-5 text-left"
                  >
                    <span
                      className={`font-serif text-lg leading-snug transition-colors duration-300 md:text-xl ${
                        isOpen ? 'text-orbit-orange' : 'group-hover:text-orbit-orange'
                      }`}
                    >
                      {faq.q}
                    </span>
                    <span
                      className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border transition-all duration-500 ${
                        isOpen
                          ? 'rotate-45 border-orbit-orange bg-orbit-orange text-white'
                          : 'border-black/15 text-orbit-ink group-hover:border-orbit-orange'
                      }`}
                      aria-hidden="true"
                    >
                      <Plus className="h-4 w-4" />
                    </span>
                  </button>
                </h3>

                <div
                  id={panelId}
                  role="region"
                  aria-labelledby={triggerId}
                  aria-hidden={!isOpen}
                  className={`grid transition-all duration-500 ease-[cubic-bezier(0.22,1,0.36,1)] ${
                    isOpen ? 'grid-rows-[1fr] opacity-100' : 'grid-rows-[0fr] opacity-0'
                  }`}
                >
                  <div className="overflow-hidden">
                    <p className="max-w-2xl pb-6 pr-10 text-[13px] leading-relaxed text-orbit-gray">
                      {faq.a}
                    </p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
