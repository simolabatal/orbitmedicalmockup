import { MessageCircle } from 'lucide-react';
import { CLINIC } from '../../data/clinic';

export default function StickyWhatsApp() {
  return (
    <a
      href={CLINIC.whatsappHref}
      target="_blank"
      rel="noopener noreferrer"
      aria-label="Poser une question médicale sur WhatsApp"
      className="group fixed bottom-5 right-5 z-40 inline-flex items-center gap-0 overflow-hidden rounded-full bg-[#1FA855] p-4 text-white shadow-[0_18px_45px_-16px_rgba(31,168,85,0.7)] transition-all duration-500 hover:bg-[#178f48] md:bottom-7 md:right-7"
    >
      <span className="absolute inset-0 -z-10 animate-[pulseRing_3s_ease-out_infinite] rounded-full" />
      <MessageCircle className="h-6 w-6 shrink-0" aria-hidden="true" />
      <span className="max-w-0 whitespace-nowrap text-[11px] font-bold uppercase tracking-[0.12em] opacity-0 transition-all duration-500 group-hover:ml-2.5 group-hover:max-w-[180px] group-hover:opacity-100">
        WhatsApp · 15 min
      </span>
      <span className="absolute -right-0.5 -top-0.5 h-3 w-3 rounded-full border-2 border-orbit-bg bg-orbit-orange" />
    </a>
  );
}
