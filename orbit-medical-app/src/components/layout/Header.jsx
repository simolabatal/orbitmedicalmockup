import { useEffect, useRef, useState } from 'react';
import { ArrowUpRight, CalendarDays, Menu, MessageCircle, Phone, X } from 'lucide-react';
import Logo from '../ui/Logo';
import { CLINIC, NAV_LINKS } from '../../data/clinic';

export default function Header({ onBook }) {
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const closeRef = useRef(null);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  useEffect(() => {
    if (!menuOpen) return undefined;

    const onKey = (event) => {
      if (event.key === 'Escape') setMenuOpen(false);
    };

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    document.addEventListener('keydown', onKey);
    closeRef.current?.focus();

    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener('keydown', onKey);
    };
  }, [menuOpen]);

  return (
    <>
      <header
        className={`sticky top-0 z-50 border-b transition-all duration-500 ${
          scrolled
            ? 'border-black/10 bg-orbit-bg/90 shadow-[0_10px_40px_-24px_rgba(0,0,0,0.35)] backdrop-blur-xl'
            : 'border-transparent bg-orbit-bg/75 backdrop-blur-md'
        }`}
      >
        <div className="shell relative flex h-20 items-center justify-between gap-4">
            <a href="#accueil" className="group z-10 flex shrink-0 items-center">
            <Logo />
          </a>

          <nav
            aria-label="Navigation principale"
            className="absolute left-1/2 top-1/2 hidden -translate-x-1/2 -translate-y-1/2 items-center gap-5 xl:flex"
          >
            {NAV_LINKS.map((link) => (
              <a
                key={link.href}
                href={link.href}
                className="link-underline whitespace-nowrap text-orbit-ink/70 hover:text-orbit-ink"
              >
                {link.label}
              </a>
            ))}
          </nav>

          <div className="z-10 flex shrink-0 items-center gap-2.5">
            <a
              href={CLINIC.phoneHref}
              className="hidden items-center gap-2 whitespace-nowrap text-[11px] font-semibold uppercase tracking-[0.12em] text-orbit-gray transition-colors hover:text-orbit-ink 2xl:flex"
            >
              <Phone className="h-3.5 w-3.5 text-orbit-orange" aria-hidden="true" />
              {CLINIC.phone}
            </a>

            <button
              type="button"
              onClick={onBook}
              className="btn-orbit btn-primary hidden whitespace-nowrap px-5 py-3 sm:inline-flex"
            >
              <CalendarDays className="h-3.5 w-3.5" aria-hidden="true" />
              Prendre rendez-vous
            </button>

            <button
              type="button"
              onClick={() => setMenuOpen(true)}
              aria-label="Ouvrir le menu"
              aria-expanded={menuOpen}
              aria-controls="mobile-menu"
              className="inline-flex h-11 w-11 items-center justify-center rounded-full border border-black/20 text-orbit-ink transition-colors hover:border-orbit-orange hover:text-orbit-orange xl:hidden"
            >
              <Menu className="h-5 w-5" aria-hidden="true" />
            </button>
          </div>
        </div>
      </header>

      {/* Menu plein écran */}
      <div
        id="mobile-menu"
        role="dialog"
        aria-modal="true"
        aria-label="Menu de navigation"
        inert={!menuOpen}
        className={`fixed inset-0 z-[80] bg-orbit-wood text-orbit-bg transition-[clip-path] duration-700 [transition-timing-function:cubic-bezier(0.22,1,0.36,1)] ${
          menuOpen ? 'pointer-events-auto [clip-path:inset(0_0_0_0)]' : 'pointer-events-none [clip-path:inset(0_0_100%_0)]'
        }`}
      >
        <div className="shell flex h-20 items-center justify-between border-b border-white/10">
          <Logo compact className="text-orbit-bg" />
          <button
            ref={closeRef}
            type="button"
            onClick={() => setMenuOpen(false)}
            aria-label="Fermer le menu"
            className="inline-flex h-11 w-11 items-center justify-center rounded-full border border-white/25 text-white transition-colors hover:border-orbit-orange hover:text-orbit-orange"
          >
            <X className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>

        <div className="shell flex h-[calc(100%-5rem)] flex-col justify-between overflow-y-auto py-10">
          <nav aria-label="Navigation mobile" className="flex flex-col">
            {NAV_LINKS.map((link, index) => (
              <a
                key={link.href}
                href={link.href}
                onClick={() => setMenuOpen(false)}
                className="group flex items-baseline gap-4 border-b border-white/10 py-4 font-serif text-3xl leading-none transition-colors hover:text-orbit-orange sm:text-4xl"
              >
                <span className="text-[10px] font-sans font-semibold uppercase tracking-[0.2em] text-white/45">
                  0{index + 1}
                </span>
                {link.label}
                <ArrowUpRight className="ml-auto h-5 w-5 opacity-0 transition-opacity group-hover:opacity-100" />
              </a>
            ))}
          </nav>

          <div className="mt-10 space-y-5">
            <button
              type="button"
              onClick={() => {
                setMenuOpen(false);
                onBook();
              }}
              className="btn-orbit btn-accent w-full"
            >
              <CalendarDays className="h-4 w-4" aria-hidden="true" />
              Réserver un créneau VIP
            </button>

            <div className="flex flex-col gap-3 text-xs text-white/60">
              <a href={CLINIC.phoneHref} className="inline-flex items-center gap-2 hover:text-white">
                <Phone className="h-3.5 w-3.5 text-orbit-orange" aria-hidden="true" />
                {CLINIC.phone}
              </a>
              <a
                href={CLINIC.whatsappHref}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 hover:text-white"
              >
                <MessageCircle className="h-3.5 w-3.5 text-orbit-orange" aria-hidden="true" />
                WhatsApp · réponse &lt; 15 min
              </a>
              <p className="pt-2 text-[11px] uppercase tracking-[0.16em] text-white/35">
                {CLINIC.address} · {CLINIC.street} · {CLINIC.district}
              </p>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
