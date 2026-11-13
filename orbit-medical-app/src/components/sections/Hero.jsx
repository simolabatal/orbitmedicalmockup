import { useLayoutEffect, useRef } from 'react';
import { ArrowDown, ArrowUpRight, BadgeCheck, CalendarDays, Clock3, MapPin } from 'lucide-react';
import { gsap, prefersReducedMotion } from '../../lib/gsap';
import { CLINIC } from '../../data/clinic';

export default function Hero({ onBook }) {
  const sectionRef = useRef(null);
  const mediaRef = useRef(null);

  useLayoutEffect(() => {
    if (prefersReducedMotion()) return undefined;

    const ctx = gsap.context(() => {
      gsap.from('[data-hero-line]', {
        yPercent: 112,
        duration: 1.15,
        stagger: 0.12,
        ease: 'power4.out',
        delay: 0.15,
      });

      gsap.from('[data-hero-fade]', {
        y: 26,
        autoAlpha: 0,
        duration: 0.9,
        stagger: 0.12,
        ease: 'power3.out',
        delay: 0.55,
      });

      gsap.to(mediaRef.current, {
        yPercent: 12,
        ease: 'none',
        scrollTrigger: {
          trigger: sectionRef.current,
          start: 'top top',
          end: 'bottom top',
          scrub: true,
        },
      });
    }, sectionRef);

    return () => ctx.revert();
  }, []);

  return (
    <section
      id="accueil"
      ref={sectionRef}
      className="relative flex min-h-[92svh] items-end overflow-hidden bg-orbit-wood text-orbit-bg"
    >
      {/* Visuel immersif */}
      <div className="absolute inset-0 z-0" aria-hidden="true">
        <img
          ref={mediaRef}
          src="https://images.unsplash.com/photo-1629909615184-74f495363b67?auto=format&fit=crop&q=85&w=2000"
          alt=""
          fetchPriority="high"
          className="h-[115%] w-full scale-105 object-cover object-center opacity-80"
        />
        <div className="absolute inset-0 bg-gradient-to-r from-orbit-wood via-orbit-wood/85 to-orbit-wood/25" />
        <div className="absolute inset-0 bg-gradient-to-t from-orbit-wood via-transparent to-orbit-wood/40" />
        <div className="dot-grid-light absolute inset-0 opacity-30" />
      </div>

      {/* Anneau orbital décoratif */}
      <div
        className="pointer-events-none absolute right-[6%] top-[18%] hidden h-64 w-64 animate-float items-center justify-center rounded-full border border-orbit-orange/30 lg:flex"
        aria-hidden="true"
      >
        <div className="h-40 w-40 rounded-full border border-white/15" />
        <span className="absolute -top-1 h-3 w-3 rounded-full bg-orbit-orange shadow-[0_0_24px_rgba(255,85,0,0.8)]" />
      </div>

      <div className="shell relative z-10 grid w-full gap-12 pb-16 pt-24 md:pt-32 lg:grid-cols-[1.15fr_0.85fr] lg:items-end lg:pb-20">
        <div>
          <p data-hero-fade className="eyebrow text-orbit-sand/90">
            Cabinet dentaire & médical d’exception · Guéliz
          </p>

          <h1 className="mt-7 text-[clamp(2.85rem,7vw,5.6rem)] font-light leading-[0.98] tracking-[-0.045em]">
            <span className="line-clip">
              <span data-hero-line className="block">
                L’art de la santé
              </span>
            </span>
            <span className="line-clip">
              <span data-hero-line className="block">
                et du <em className="font-serif italic text-orbit-orange">sourire.</em>
              </span>
            </span>
            <span className="line-clip">
              <span data-hero-line className="block text-orbit-sand">
                Précision & sérénité.
              </span>
            </span>
          </h1>

          <p
            data-hero-fade
            className="mt-8 max-w-xl text-[15px] leading-relaxed text-white/65 md:text-base"
          >
            Au cœur de Guéliz, Orbit Medical conjugue imagerie 3D, stérilisation de
            classe B et approche humaine 1:1 pour redéfinir l’expérience du soin à
            Marrakech.
          </p>

          <div data-hero-fade className="mt-9 flex flex-col gap-3 sm:flex-row">
            <button
              type="button"
              onClick={onBook}
              className="btn-orbit btn-accent w-full sm:w-auto"
            >
              <CalendarDays className="h-4 w-4" aria-hidden="true" />
              Prendre rendez-vous en ligne
            </button>
            <a href="#soins" className="btn-orbit btn-on-dark w-full sm:w-auto">
              Découvrir nos soins
              <ArrowUpRight className="h-4 w-4" aria-hidden="true" />
            </a>
          </div>
        </div>

        {/* Carte FOMO + accès */}
        <div data-hero-fade className="space-y-3 lg:justify-self-end">
          <div className="w-full max-w-sm rounded-2xl border border-white/15 bg-white/[0.07] p-5 backdrop-blur-md">
            <div className="flex items-center justify-between gap-3">
              <span className="inline-flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.16em] text-orbit-sand">
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-orbit-orange opacity-75" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-orbit-orange" />
                </span>
                Agenda VIP
              </span>
              <span className="rounded-full bg-orbit-orange px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.1em] text-orbit-ink">
                3 places
              </span>
            </div>
            <p className="mt-3 font-serif text-xl leading-snug text-white">
              Il reste 3 créneaux de consultation cette semaine.
            </p>
            <button
              type="button"
              onClick={onBook}
              className="link-underline mt-4 text-orbit-sand hover:text-white"
            >
              Réserver mon créneau
              <ArrowUpRight className="h-3.5 w-3.5" aria-hidden="true" />
            </button>
          </div>

          <div className="w-full max-w-sm rounded-2xl border border-white/10 bg-orbit-wood/55 p-5 text-xs text-white/65 backdrop-blur-md">
            <div className="flex items-start gap-3">
              <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-orbit-orange" aria-hidden="true" />
              <p>
                <span className="font-semibold text-white">{CLINIC.address}</span>
                <br />
                {CLINIC.street}, {CLINIC.district}
              </p>
            </div>
            <div className="mt-3 flex items-center gap-3">
              <Clock3 className="h-4 w-4 shrink-0 text-orbit-orange" aria-hidden="true" />
              {CLINIC.hours}
            </div>
            <div className="mt-3 flex items-center gap-3">
              <BadgeCheck className="h-4 w-4 shrink-0 text-orbit-orange" aria-hidden="true" />
              Stérilisation classe B · Normes européennes
            </div>
          </div>
        </div>
      </div>

      <div className="pointer-events-none absolute bottom-6 left-1/2 z-10 hidden -translate-x-1/2 flex-col items-center gap-2 text-[9px] font-bold uppercase tracking-[0.22em] text-white/40 md:flex">
        Défiler
        <ArrowDown className="h-3.5 w-3.5 animate-bounce text-orbit-orange" aria-hidden="true" />
      </div>
    </section>
  );
}
