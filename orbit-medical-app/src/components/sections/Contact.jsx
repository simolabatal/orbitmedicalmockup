import { ArrowUpRight, CalendarDays, Clock3, MapPin, MessageCircle, Phone } from 'lucide-react';
import { CLINIC } from '../../data/clinic';

const CONTACT_ROWS = [
  {
    icon: MapPin,
    label: 'Adresse',
    value: `${CLINIC.address}, ${CLINIC.street}, ${CLINIC.district}`,
  },
  { icon: Clock3, label: 'Horaires', value: CLINIC.hours },
  { icon: Phone, label: 'Ligne directe', value: CLINIC.phone, href: CLINIC.phoneHref },
  {
    icon: MessageCircle,
    label: 'WhatsApp médical',
    value: `${CLINIC.whatsapp} · réponse < 15 min`,
    href: CLINIC.whatsappHref,
  },
];

export default function Contact({ onBook }) {
  return (
    <section id="contact" className="border-y border-orbit-sand bg-orbit-sand/25 py-24 md:py-32">
      <div className="shell grid gap-12 lg:grid-cols-[0.95fr_1.05fr] lg:items-center">
        <div data-reveal>
          <p className="eyebrow text-orbit-gray">Contact & accès · Guéliz</p>
          <h2 className="mt-5 text-[clamp(2.2rem,4.6vw,4rem)] leading-[1.02]">
            Votre rendez-vous
            <br />
            à <em className="italic text-orbit-orange">Marrakech.</em>
          </h2>
          <p className="mt-5 max-w-lg text-sm leading-relaxed text-orbit-gray">
            Un cabinet pensé comme un écrin : accès sécurisé, parking privé au pied de
            l’immeuble et accueil sans attente. Nous recevons également les patients
            internationaux sur rendez-vous coordonné.
          </p>

          <ul className="mt-8 divide-y divide-black/10 border-y border-black/10">
            {CONTACT_ROWS.map((row) => {
              const Icon = row.icon;
              const content = row.href ? (
                <a
                  href={row.href}
                  target={row.href.startsWith('http') ? '_blank' : undefined}
                  rel={row.href.startsWith('http') ? 'noopener noreferrer' : undefined}
                  className="transition-colors hover:text-orbit-orange"
                >
                  {row.value}
                </a>
              ) : (
                row.value
              );

              return (
                <li key={row.label} className="flex items-start gap-4 py-4">
                  <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-white text-orbit-orange">
                    <Icon className="h-4 w-4" aria-hidden="true" />
                  </span>
                  <div>
                    <p className="text-[9px] font-bold uppercase tracking-[0.16em] text-orbit-gray">
                      {row.label}
                    </p>
                    <p className="mt-1 text-sm font-medium leading-snug text-orbit-ink">
                      {content}
                    </p>
                  </div>
                </li>
              );
            })}
          </ul>

          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <button
              type="button"
              onClick={onBook}
              className="btn-orbit btn-primary w-full sm:w-auto"
            >
              <CalendarDays className="h-4 w-4" aria-hidden="true" />
              Réserver en ligne
            </button>
            <a
              href={CLINIC.whatsappHref}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-orbit btn-ghost w-full sm:w-auto"
            >
              <MessageCircle className="h-4 w-4" aria-hidden="true" />
              WhatsApp
            </a>
          </div>
        </div>

        <div data-reveal data-delay="0.1" className="relative">
          <div className="relative aspect-[4/3] overflow-hidden rounded-2xl border border-black/10 shadow-xl">
            <img
              src="https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?auto=format&fit=crop&q=80&w=1400"
              alt="Immeuble et quartier de Guéliz à Marrakech"
              loading="lazy"
              className="h-full w-full object-cover"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-orbit-wood/85 via-orbit-wood/25 to-transparent" />

            <div className="absolute inset-x-5 bottom-5 rounded-xl border border-white/20 bg-orbit-wood/70 p-5 text-orbit-bg backdrop-blur-md">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-[9px] font-bold uppercase tracking-[0.16em] text-orbit-sand">
                    Orbit Medical · Guéliz
                  </p>
                  <p className="mt-2 font-serif text-xl leading-snug">
                    {CLINIC.address}
                  </p>
                  <p className="mt-1 text-xs text-white/60">
                    {CLINIC.street} · {CLINIC.postal}
                  </p>
                </div>
                <a
                  href={CLINIC.mapsUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label="Ouvrir l'adresse dans Google Maps"
                  className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-orbit-orange text-white transition-colors hover:bg-white hover:text-orbit-ink"
                >
                  <ArrowUpRight className="h-5 w-5" aria-hidden="true" />
                </a>
              </div>
            </div>

            <span className="absolute left-5 top-5 inline-flex items-center gap-2 rounded-full border border-white/25 bg-orbit-wood/55 px-3 py-1.5 text-[9px] font-bold uppercase tracking-[0.12em] text-white backdrop-blur">
              <span className="h-1.5 w-1.5 rounded-full bg-orbit-orange" aria-hidden="true" />
              Parking privé · Accès sécurisé
            </span>
          </div>

          <p className="mt-4 text-center text-[10px] uppercase tracking-[0.14em] text-orbit-gray">
            À 4 minutes de la place du 16 Novembre · Guéliz
          </p>
        </div>
      </div>
    </section>
  );
}
