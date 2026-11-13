import { TRUST_STATS } from '../../data/clinic';

export default function TrustStats() {
  return (
    <section className="border-b border-black/10 bg-orbit-bg">
      <div className="shell grid grid-cols-2 divide-x divide-black/10 py-10 md:grid-cols-4 md:py-12">
        {TRUST_STATS.map((stat) => (
          <div key={stat.label} className="px-4 py-3 text-center md:px-8">
            <p className="font-serif text-3xl font-light tracking-tight md:text-5xl">
              {stat.value}
            </p>
            <p className="mt-2 text-[9px] font-semibold uppercase tracking-[0.16em] text-orbit-gray md:text-[10px]">
              {stat.label}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}
