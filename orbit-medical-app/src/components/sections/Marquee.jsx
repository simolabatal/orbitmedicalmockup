import { MARQUEE_ITEMS } from '../../data/clinic';

export default function Marquee() {
  const items = [...MARQUEE_ITEMS, ...MARQUEE_ITEMS];

  return (
    <div className="overflow-hidden border-y border-black/10 bg-orbit-sand/70 py-4">
      <div className="marquee-track flex w-max items-center">
        {items.map((item, index) => (
          <span
            key={`${item}-${index}`}
            aria-hidden={index >= MARQUEE_ITEMS.length}
            className="flex shrink-0 items-center gap-6 px-6 text-[10px] font-bold uppercase tracking-[0.24em] text-orbit-wood/70"
          >
            {item}
            <span className="h-1 w-1 rounded-full bg-orbit-orange" aria-hidden="true" />
          </span>
        ))}
      </div>
    </div>
  );
}
