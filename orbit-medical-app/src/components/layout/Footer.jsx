import { ArrowUpRight, MapPin, MessageCircle, Phone } from 'lucide-react';
import Logo from '../ui/Logo';
import { CLINIC, NAV_LINKS } from '../../data/clinic';

export default function Footer({ onBook }) {
  return (
    <footer className="relative overflow-hidden bg-orbit-wood text-orbit-bg">
      <div className="dot-grid-light pointer-events-none absolute inset-0 opacity-40" aria-hidden="true" />
      <div className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full border border-white/10" aria-hidden="true" />
      <div className="pointer-events-none absolute -right-10 -top-10 h-44 w-44 rounded-full border border-orbit-orange/30" aria-hidden="true" />

      <div className="shell relative py-16 md:py-20">
        <div className="grid gap-12 border-b border-white/10 pb-14 lg:grid-cols-[1.4fr_1fr_1fr]">
          <div>
            <Logo compact className="text-orbit-bg" />
            <p className="mt-6 max-w-sm text-sm leading-relaxed text-white/55">
              Cabinet médical et dentaire de pointe à Guéliz, Marrakech. Technologie 3D,
              stérilisation de classe B et excellence esthétique, au service d’une
              patientèle exigeante.
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              <a
                href={CLINIC.whatsappHref}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 rounded-full border border-white/20 px-4 py-2.5 text-[10px] font-bold uppercase tracking-[0.14em] text-white transition-colors hover:border-[#25D366] hover:text-[#5CE08B]"
              >
                <MessageCircle className="h-3.5 w-3.5" aria-hidden="true" />
                WhatsApp
              </a>
              <button
                type="button"
                onClick={onBook}
                className="inline-flex items-center gap-2 rounded-full bg-orbit-orange px-4 py-2.5 text-[10px] font-bold uppercase tracking-[0.14em] text-orbit-ink transition-colors hover:bg-white hover:text-orbit-ink"
              >
                Prendre rendez-vous
                <ArrowUpRight className="h-3.5 w-3.5" aria-hidden="true" />
              </button>
            </div>
          </div>

          <div>
            <h3 className="text-[10px] font-sans font-bold uppercase tracking-[0.2em] text-white/40">
              Navigation
            </h3>
            <ul className="mt-5 space-y-3 text-sm text-white/65">
              {NAV_LINKS.map((link) => (
                <li key={link.href}>
                  <a href={link.href} className="transition-colors hover:text-orbit-orange">
                    {link.label}
                  </a>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h3 className="text-[10px] font-sans font-bold uppercase tracking-[0.2em] text-white/40">
              Contact & accès
            </h3>
            <ul className="mt-5 space-y-4 text-sm text-white/65">
              <li className="flex gap-3">
                <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-orbit-orange" aria-hidden="true" />
                <span>
                  {CLINIC.address}
                  <br />
                  {CLINIC.street}
                  <br />
                  {CLINIC.postal}
                </span>
              </li>
              <li>
                <a href={CLINIC.phoneHref} className="flex items-center gap-3 hover:text-white">
                  <Phone className="h-4 w-4 shrink-0 text-orbit-orange" aria-hidden="true" />
                  {CLINIC.phone}
                </a>
              </li>
              <li className="text-xs leading-relaxed text-white/45">
                {CLINIC.hours}
                <br />
                {CLINIC.hoursDetail}
              </li>
            </ul>
          </div>
        </div>

        <div className="flex flex-col gap-4 pt-7 text-[10px] uppercase tracking-[0.16em] text-white/35 md:flex-row md:items-center md:justify-between">
          <p>© {new Date().getFullYear()} Orbit Medical Marrakech · Tous droits réservés</p>
          <p>Conception Orbit Studio · Maquette de démonstration</p>
        </div>
      </div>
    </footer>
  );
}
