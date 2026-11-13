import { useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import {
  ArrowLeft,
  ArrowRight,
  CalendarDays,
  Check,
  CheckCircle2,
  Clock3,
  Download,
  ExternalLink,
  ShieldCheck,
  Sparkles,
  X,
} from 'lucide-react';
import confetti from 'canvas-confetti';
import { TIME_SLOTS, TREATMENTS } from '../../data/clinic';
import {
  buildGoogleCalendarUrl,
  downloadICS,
  formatFrenchDate,
  formatFrenchTime,
  generateBookingCode,
  isValidEmail,
  isValidMoroccanPhone,
} from '../../lib/calendar';
import { prefersReducedMotion } from '../../lib/gsap';
import { startSmoothScroll, stopSmoothScroll } from '../../lib/scroll';

const STEP_LABELS = ['Soin & créneau', 'Coordonnées', 'Confirmation'];

const tomorrowISO = () => {
  const date = new Date();
  date.setDate(date.getDate() + 1);
  return date.toISOString().slice(0, 10);
};

const todayISO = () => new Date().toISOString().slice(0, 10);

const maxISO = () => {
  const date = new Date();
  date.setDate(date.getDate() + 90);
  return date.toISOString().slice(0, 10);
};

export default function BookingModal({ open, initialTreatment, onClose }) {
  const [step, setStep] = useState(1);
  const [treatmentId, setTreatmentId] = useState(TREATMENTS[0].id);
  const [date, setDate] = useState(tomorrowISO());
  const [time, setTime] = useState(TIME_SLOTS[0].value);
  const [form, setForm] = useState({ name: '', phone: '+212 ', email: '' });
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [code, setCode] = useState('');

  const panelRef = useRef(null);
  const closeRef = useRef(null);
  const timerRef = useRef(null);

  const treatment = useMemo(
    () => TREATMENTS.find((item) => item.id === treatmentId) || TREATMENTS[0],
    [treatmentId]
  );

  // Réinitialisation à chaque ouverture (et présélection du soin cliqué)
  useEffect(() => {
    if (!open) return;

    setStep(1);
    setTreatmentId(initialTreatment?.id || TREATMENTS[0].id);
    setDate(tomorrowISO());
    setTime(TIME_SLOTS[0].value);
    setForm({ name: '', phone: '+212 ', email: '' });
    setErrors({});
    setSubmitting(false);
    setCode('');
  }, [open, initialTreatment]);

  // Verrouillage du scroll, arrêt de Lenis, fermeture Échap, focus initial
  useEffect(() => {
    if (!open) return undefined;

    stopSmoothScroll();
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    const onKeyDown = (event) => {
      if (event.key === 'Escape') {
        onClose();
        return;
      }
      if (event.key !== 'Tab' || !panelRef.current) return;

      const focusables = panelRef.current.querySelectorAll(
        'a[href], button:not([disabled]), input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      if (!focusables.length) return;

      const first = focusables[0];
      const last = focusables[focusables.length - 1];

      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener('keydown', onKeyDown);
    const focusTimer = window.setTimeout(() => closeRef.current?.focus(), 60);

    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener('keydown', onKeyDown);
      window.clearTimeout(focusTimer);
      window.clearTimeout(timerRef.current);
      startSmoothScroll();
    };
  }, [open, onClose]);

  if (!open) return null;

  const updateForm = (field, value) => {
    setForm((current) => ({ ...current, [field]: value }));
    setErrors((current) => ({ ...current, [field]: undefined }));
  };

  const goToStepTwo = (event) => {
    event.preventDefault();
    setStep(2);
  };

  const validate = () => {
    const nextErrors = {};

    if (form.name.trim().length < 2) {
      nextErrors.name = 'Merci d’indiquer votre nom complet.';
    }
    if (!isValidMoroccanPhone(form.phone)) {
      nextErrors.phone = 'Format attendu : +212 6 12 34 56 78 ou 06 12 34 56 78.';
    }
    if (!isValidEmail(form.email)) {
      nextErrors.email = 'Merci d’indiquer une adresse e-mail valide.';
    }

    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const submit = (event) => {
    event.preventDefault();
    if (!validate()) return;

    setSubmitting(true);
    timerRef.current = window.setTimeout(() => {
      const generated = generateBookingCode();
      setCode(generated);
      setSubmitting(false);
      setStep(3);

      if (!prefersReducedMotion()) {
        confetti({
          particleCount: 90,
          spread: 72,
          origin: { y: 0.6 },
          colors: ['#FF5500', '#2C1F18', '#E9DCC6'],
        });
      }
    }, 900);
  };

  const googleCalendarUrl = buildGoogleCalendarUrl({
    treatment: treatment.name,
    code,
    dateISO: date,
    time,
  });

  const handleICS = () => {
    downloadICS(
      {
        treatment: treatment.name,
        code,
        dateISO: date,
        time,
        name: form.name,
      },
      `orbit-medical-${code}.ics`
    );
  };

  return createPortal(
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="booking-title"
        data-lenis-prevent
        className="relative max-h-[92vh] w-full max-w-2xl overflow-y-auto rounded-2xl border border-white/10 bg-orbit-bg shadow-2xl"
      >
        {/* En-tête */}
        <div className="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-white/10 bg-orbit-wood px-6 py-5 text-orbit-bg md:px-8">
          <div>
            <p className="inline-flex items-center gap-2 text-[9px] font-bold uppercase tracking-[0.2em] text-orbit-orange">
              <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
              Réservation VIP · Guéliz
            </p>
            <h2 id="booking-title" className="mt-2 font-serif text-2xl leading-none md:text-3xl">
              {step === 3 ? 'Votre rendez-vous est confirmé.' : 'Prendre rendez-vous'}
            </h2>
          </div>
          <button
            ref={closeRef}
            type="button"
            onClick={onClose}
            aria-label="Fermer la fenêtre de réservation"
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-white/20 text-white transition-colors hover:border-orbit-orange hover:bg-orbit-orange"
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>

        <div className="px-6 py-6 md:px-8 md:py-8">
          {/* Fil d'étapes */}
          <ol className="mb-7 flex items-center gap-2" aria-label="Étapes de la réservation">
            {STEP_LABELS.map((label, index) => {
              const stepNumber = index + 1;
              const done = step > stepNumber;
              const current = step === stepNumber;

              return (
                <li key={label} className="flex flex-1 items-center gap-2">
                  <span
                    className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[10px] font-bold transition-colors ${
                      done || current
                        ? 'bg-orbit-orange text-orbit-ink'
                        : 'border border-black/15 text-orbit-gray'
                    }`}
                    aria-hidden="true"
                  >
                    {done ? <Check className="h-3 w-3" /> : stepNumber}
                  </span>
                  <span
                    className={`hidden text-[9px] font-bold uppercase tracking-[0.1em] sm:block ${
                      current ? 'text-orbit-ink' : 'text-orbit-gray'
                    }`}
                  >
                    {label}
                  </span>
                  {index < STEP_LABELS.length - 1 ? (
                    <span
                      className={`ml-auto h-px flex-1 ${
                        done ? 'bg-orbit-orange' : 'bg-black/10'
                      }`}
                      aria-hidden="true"
                    />
                  ) : null}
                </li>
              );
            })}
          </ol>

          {/* ÉTAPE 1 */}
          {step === 1 ? (
            <form onSubmit={goToStepTwo} className="space-y-6">
              <div>
                <label
                  htmlFor="booking-treatment"
                  className="mb-2 block text-[10px] font-bold uppercase tracking-[0.14em] text-orbit-gray"
                >
                  Soin ou consultation
                </label>
                <select
                  id="booking-treatment"
                  value={treatmentId}
                  onChange={(event) => setTreatmentId(event.target.value)}
                  className="w-full rounded-xl border border-black/15 bg-white px-4 py-3.5 text-sm font-medium outline-none transition-colors focus:border-orbit-orange"
                >
                  {TREATMENTS.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.name} — {item.price}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid gap-5 sm:grid-cols-2">
                <div>
                  <label
                    htmlFor="booking-date"
                    className="mb-2 flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.14em] text-orbit-gray"
                  >
                    <CalendarDays className="h-3.5 w-3.5 text-orbit-orange" aria-hidden="true" />
                    Date souhaitée
                  </label>
                  <input
                    id="booking-date"
                    type="date"
                    value={date}
                    min={todayISO()}
                    max={maxISO()}
                    onChange={(event) => setDate(event.target.value)}
                    required
                    className="w-full rounded-xl border border-black/15 bg-white px-4 py-3.5 text-sm font-medium outline-none transition-colors focus:border-orbit-orange"
                  />
                </div>

                <div>
                  <span className="mb-2 flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.14em] text-orbit-gray">
                    <Clock3 className="h-3.5 w-3.5 text-orbit-orange" aria-hidden="true" />
                    Créneau horaire
                  </span>
                  <div className="grid grid-cols-2 gap-2" role="group" aria-label="Créneau horaire">
                    {TIME_SLOTS.map((slot) => {
                      const selected = slot.value === time;
                      return (
                        <button
                          key={slot.value}
                          type="button"
                          aria-pressed={selected}
                          onClick={() => setTime(slot.value)}
                          className={`rounded-xl border px-3 py-2.5 text-left transition-colors duration-300 ${
                            selected
                              ? 'border-orbit-orange bg-orbit-orange text-orbit-ink'
                              : 'border-black/15 bg-white text-orbit-ink hover:border-orbit-orange'
                          }`}
                        >
                          <span className="block text-sm font-semibold">{slot.label}</span>
                          <span
                            className={`mt-0.5 block text-[9px] font-medium uppercase tracking-[0.1em] ${
                              selected ? 'text-orbit-ink/70' : 'text-orbit-gray'
                            }`}
                          >
                            {slot.note}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              </div>

              <div className="rounded-xl border border-orbit-sand bg-orbit-sand/25 p-4 text-xs text-orbit-gray">
                <div className="flex items-start gap-3">
                  <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-orbit-orange" aria-hidden="true" />
                  <p>
                    <span className="font-semibold text-orbit-ink">
                      {treatment.name}
                    </span>{' '}
                    · {formatFrenchDate(date, { year: undefined })} à{' '}
                    {formatFrenchTime(time)}. Durée estimée : {treatment.duration}.
                  </p>
                </div>
              </div>

              <button type="submit" className="btn-orbit btn-accent w-full">
                Continuer vers mes coordonnées
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </button>
            </form>
          ) : null}

          {/* ÉTAPE 2 */}
          {step === 2 ? (
            <form onSubmit={submit} className="space-y-5" noValidate>
              <div className="flex flex-col gap-3 rounded-xl border border-black/10 bg-white p-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-[9px] font-bold uppercase tracking-[0.14em] text-orbit-gray">
                    Récapitulatif
                  </p>
                  <p className="mt-1 font-serif text-lg leading-tight">{treatment.name}</p>
                  <p className="mt-1 text-xs text-orbit-orange">
                    {formatFrenchDate(date)} · {formatFrenchTime(time)}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setStep(1)}
                  className="self-start text-[10px] font-bold uppercase tracking-[0.12em] underline decoration-black/20 underline-offset-4 transition-colors hover:text-orbit-orange sm:self-auto"
                >
                  Modifier
                </button>
              </div>

              <div>
                <label
                  htmlFor="booking-name"
                  className="mb-2 block text-[10px] font-bold uppercase tracking-[0.14em] text-orbit-gray"
                >
                  Nom et prénom
                </label>
                <input
                  id="booking-name"
                  type="text"
                  autoComplete="name"
                  value={form.name}
                  onChange={(event) => updateForm('name', event.target.value)}
                  placeholder="Ex. Yasmine Benjelloun"
                  aria-invalid={Boolean(errors.name)}
                  aria-describedby={errors.name ? 'booking-name-error' : undefined}
                  className={`w-full rounded-xl border bg-white px-4 py-3.5 text-sm outline-none transition-colors focus:border-orbit-orange ${
                    errors.name ? 'border-red-500' : 'border-black/15'
                  }`}
                />
                {errors.name ? (
                  <p id="booking-name-error" className="mt-1.5 text-[11px] text-red-600">
                    {errors.name}
                  </p>
                ) : null}
              </div>

              <div>
                <label
                  htmlFor="booking-phone"
                  className="mb-2 block text-[10px] font-bold uppercase tracking-[0.14em] text-orbit-gray"
                >
                  Téléphone marocain · +212
                </label>
                <input
                  id="booking-phone"
                  type="tel"
                  inputMode="tel"
                  autoComplete="tel"
                  value={form.phone}
                  onChange={(event) => updateForm('phone', event.target.value)}
                  placeholder="+212 6 12 34 56 78"
                  aria-invalid={Boolean(errors.phone)}
                  aria-describedby={errors.phone ? 'booking-phone-error' : undefined}
                  className={`w-full rounded-xl border bg-white px-4 py-3.5 text-sm outline-none transition-colors focus:border-orbit-orange ${
                    errors.phone ? 'border-red-500' : 'border-black/15'
                  }`}
                />
                {errors.phone ? (
                  <p id="booking-phone-error" className="mt-1.5 text-[11px] text-red-600">
                    {errors.phone}
                  </p>
                ) : null}
              </div>

              <div>
                <label
                  htmlFor="booking-email"
                  className="mb-2 block text-[10px] font-bold uppercase tracking-[0.14em] text-orbit-gray"
                >
                  Adresse e-mail
                </label>
                <input
                  id="booking-email"
                  type="email"
                  autoComplete="email"
                  value={form.email}
                  onChange={(event) => updateForm('email', event.target.value)}
                  placeholder="vous@exemple.com"
                  aria-invalid={Boolean(errors.email)}
                  aria-describedby={errors.email ? 'booking-email-error' : undefined}
                  className={`w-full rounded-xl border bg-white px-4 py-3.5 text-sm outline-none transition-colors focus:border-orbit-orange ${
                    errors.email ? 'border-red-500' : 'border-black/15'
                  }`}
                />
                {errors.email ? (
                  <p id="booking-email-error" className="mt-1.5 text-[11px] text-red-600">
                    {errors.email}
                  </p>
                ) : null}
              </div>

              <p className="text-[10px] leading-relaxed text-orbit-gray">
                Vos informations restent confidentielles et sont utilisées uniquement
                pour confirmer votre rendez-vous. Aucune donnée médicale n’est
                transmise par ce formulaire.
              </p>

              <div className="flex flex-col gap-3 sm:flex-row">
                <button
                  type="button"
                  onClick={() => setStep(1)}
                  className="btn-orbit btn-ghost w-full sm:w-auto"
                >
                  <ArrowLeft className="h-4 w-4" aria-hidden="true" />
                  Retour
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="btn-orbit btn-accent w-full flex-1"
                >
                  {submitting ? 'Enregistrement…' : 'Confirmer mon rendez-vous'}
                  {!submitting ? <ArrowRight className="h-4 w-4" aria-hidden="true" /> : null}
                </button>
              </div>
            </form>
          ) : null}

          {/* ÉTAPE 3 */}
          {step === 3 ? (
            <div className="text-center">
              <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full border border-orbit-orange/30 bg-orbit-orange/10 text-orbit-orange">
                <CheckCircle2 className="h-8 w-8" aria-hidden="true" />
              </div>

              <p className="mt-5 text-[10px] font-bold uppercase tracking-[0.2em] text-orbit-orange">
                Rendez-vous confirmé
              </p>
              <h3 className="mt-2 font-serif text-3xl leading-tight">
                Merci, {form.name.split(' ')[0]}.
              </h3>
              <p className="mx-auto mt-3 max-w-md text-sm leading-relaxed text-orbit-gray">
                Votre créneau est réservé chez Orbit Medical, Guéliz. Conservez votre
                code de réservation :
              </p>

              <div className="mx-auto mt-5 inline-block rounded-xl border border-orbit-sand bg-orbit-wood px-6 py-3 font-mono text-lg font-bold tracking-[0.18em] text-orbit-sand">
                {code}
              </div>

              <dl className="mx-auto mt-6 grid max-w-md gap-2 rounded-xl border border-black/10 bg-white p-4 text-left text-xs">
                <div className="flex justify-between gap-4">
                  <dt className="text-orbit-gray">Soin</dt>
                  <dd className="text-right font-medium">{treatment.name}</dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-orbit-gray">Date</dt>
                  <dd className="text-right font-medium">{formatFrenchDate(date)}</dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-orbit-gray">Heure</dt>
                  <dd className="text-right font-medium">{formatFrenchTime(time)}</dd>
                </div>
              </dl>

              <div className="mt-6 space-y-3">
                <a
                  href={googleCalendarUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-orbit btn-primary w-full"
                >
                  <ExternalLink className="h-4 w-4" aria-hidden="true" />
                  Ajouter à Google Calendar
                </a>
                <button type="button" onClick={handleICS} className="btn-orbit btn-ghost w-full">
                  <Download className="h-4 w-4" aria-hidden="true" />
                  Télécharger le fichier .ics (Apple / Android)
                </button>
              </div>

              <p className="mt-5 text-[10px] leading-relaxed text-orbit-gray">
                Un récapitulatif est envoyé à {form.email}. Pour toute modification,
                contactez-nous au +212 5 24 43 00 00.
              </p>

              <button
                type="button"
                onClick={onClose}
                className="mt-5 text-[10px] font-bold uppercase tracking-[0.12em] underline decoration-black/20 underline-offset-4 transition-colors hover:text-orbit-orange"
              >
                Fermer cette fenêtre
              </button>
            </div>
          ) : null}
        </div>
      </div>
    </div>,
    document.body
  );
}
