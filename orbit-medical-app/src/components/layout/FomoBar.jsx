import { ArrowUpRight } from 'lucide-react';
import { CLINIC } from '../../data/clinic';

export default function FomoBar({ onBook }) {
  return (
    <div className="relative z-[55] bg-orbit-wood text-orbit-bg">
      <div className="shell flex min-h-[38px] flex-wrap items-center justify-center gap-x-3 gap-y-1 py-2 text-center text-[11px] font-medium tracking-wide">
        <span className="relative flex h-2 w-2 shrink-0">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-orbit-orange opacity-70" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-orbit-orange" />
        </span>
        <span className="text-white/75">
          Exclusivité {CLINIC.district} :{' '}
          <strong className="font-semibold text-white">
            il reste 3 créneaux VIP de consultation
          </strong>{' '}
          cette semaine.
        </span>
        <button
          type="button"
          onClick={onBook}
          className="hidden items-center gap-1 text-[10px] font-bold uppercase tracking-[0.14em] text-orbit-sand transition-colors hover:text-orbit-orange sm:inline-flex"
        >
          Réserver
          <ArrowUpRight className="h-3 w-3" aria-hidden="true" />
        </button>
      </div>
    </div>
  );
}
