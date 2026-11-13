const CALENDAR_TIMEZONE = 'Africa/Casablanca';

const pad = (value) => String(value).padStart(2, '0');

/** Découpe une date ISO et une heure ("09:30") en bornes locales d'une heure. */
export function getSlotRange(dateISO, startTime) {
  const [year, month, day] = dateISO.split('-').map(Number);
  const [hours, minutes] = startTime.split(':').map(Number);

  if (!year || !month || !day || Number.isNaN(hours) || Number.isNaN(minutes)) {
    return null;
  }

  const start = `${year}${pad(month)}${pad(day)}T${pad(hours)}${pad(minutes)}00`;
  const endHour = (hours + 1) % 24;
  const end = `${year}${pad(month)}${pad(day)}T${pad(endHour)}${pad(minutes)}00`;
  const endDate = new Date(year, month - 1, day, hours + 1, minutes);

  return {
    start,
    end,
    startDateTime: new Date(year, month - 1, day, hours, minutes),
    endDateTime: endDate,
  };
}

export function formatFrenchDate(dateISO, options = {}) {
  const date = new Date(`${dateISO}T12:00:00`);
  if (Number.isNaN(date.getTime())) return '';
  return new Intl.DateTimeFormat('fr-FR', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    ...options,
  }).format(date);
}

export function formatFrenchTime(time) {
  return time ? time.replace(':', 'h') : '';
}

export function buildGoogleCalendarUrl({ treatment, code, dateISO, time }) {
  const range = getSlotRange(dateISO, time);
  if (!range) return '#';

  const params = new URLSearchParams({
    action: 'TEMPLATE',
    text: `Consultation Orbit Medical — ${treatment} (${code})`,
    details: [
      'Votre rendez-vous au cabinet Orbit Medical, Guéliz, Marrakech.',
      `Code de réservation : ${code}`,
      'Téléphone : +212 5 24 43 00 00',
    ].join('\n'),
    location:
      "Centre d'Affaires Jawhara, Boulevard Moulay Rachid, Guéliz, 40000 Marrakech",
    dates: `${range.start}/${range.end}`,
    ctz: CALENDAR_TIMEZONE,
  });

  return `https://calendar.google.com/calendar/render?${params.toString()}`;
}

/** Échappement RFC 5545 pour les champs texte d'un fichier .ics */
function escapeICS(value) {
  return String(value)
    .replace(/\\/g, '\\\\')
    .replace(/\n/g, '\\n')
    .replace(/,/g, '\\,')
    .replace(/;/g, '\\;');
}

function utcStamp(date = new Date()) {
  return `${date.getUTCFullYear()}${pad(date.getUTCMonth() + 1)}${pad(
    date.getUTCDate()
  )}T${pad(date.getUTCHours())}${pad(date.getUTCMinutes())}${pad(
    date.getUTCSeconds()
  )}Z`;
}

export function buildICS({ treatment, code, dateISO, time, name }) {
  const range = getSlotRange(dateISO, time);
  if (!range) return '';

  const lines = [
    'BEGIN:VCALENDAR',
    'VERSION:2.0',
    'PRODID:-//Orbit Medical//Marrakech//FR',
    'CALSCALE:GREGORIAN',
    'METHOD:PUBLISH',
    'BEGIN:VEVENT',
    `UID:${code}-${Date.now()}@orbit-medical.ma`,
    `DTSTAMP:${utcStamp()}`,
    `SUMMARY:${escapeICS(`Consultation Orbit Medical — ${treatment}`)}`,
    `DESCRIPTION:${escapeICS(
      `Rendez-vous de prestige chez Orbit Medical, Guéliz, Marrakech.\nCode de réservation : ${code}\nPatient : ${name}\nTéléphone : +212 5 24 43 00 00`
    )}`,
    `LOCATION:${escapeICS(
      "Centre d'Affaires Jawhara, Boulevard Moulay Rachid, Guéliz, 40000 Marrakech"
    )}`,
    `DTSTART;TZID=${CALENDAR_TIMEZONE}:${range.start}`,
    `DTEND;TZID=${CALENDAR_TIMEZONE}:${range.end}`,
    'BEGIN:VALARM',
    'ACTION:DISPLAY',
    'DESCRIPTION:Rappel — Consultation Orbit Medical',
    'TRIGGER:-PT2H',
    'END:VALARM',
    'END:VEVENT',
    'END:VCALENDAR',
  ];

  return lines.join('\r\n');
}

export function downloadICS(payload, filename) {
  const content = buildICS(payload);
  if (!content) return;

  const blob = new Blob([`\uFEFF${content}`], {
    type: 'text/calendar;charset=utf-8',
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export function generateBookingCode() {
  return `ORB-MED-${Math.floor(1000 + Math.random() * 9000)}`;
}

export function isValidMoroccanPhone(phone) {
  const normalized = phone.replace(/[\s.-]/g, '');
  return /^(?:\+212|0)[5-7]\d{8}$/.test(normalized);
}

export function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email.trim());
}
