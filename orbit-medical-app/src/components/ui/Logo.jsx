export default function Logo({ compact = false, className = '' }) {
  return (
    <span className={`flex items-center gap-3 ${className}`}>
      <svg
        viewBox="0 0 48 48"
        aria-hidden="true"
        className="h-9 w-9 shrink-0 text-current transition-transform duration-700 group-hover:rotate-45"
      >
        <circle cx="24" cy="24" r="17.5" fill="none" stroke="currentColor" strokeWidth="1.2" />
        <ellipse
          cx="24"
          cy="24"
          rx="22"
          ry="7.5"
          fill="none"
          stroke="currentColor"
          strokeWidth="0.7"
          transform="rotate(-28 24 24)"
          opacity="0.45"
        />
        <circle cx="24" cy="6.5" r="3.6" fill="#FF5500" />
      </svg>
      <span className="flex flex-col leading-none">
        <span className="text-[15px] font-bold tracking-[0.2em]">ORBIT</span>
        <span
          className={`mt-1 text-[8.5px] font-semibold uppercase tracking-[0.26em] ${
            compact ? 'text-current opacity-60' : 'text-orbit-gray'
          }`}
        >
          Medical · Marrakech
        </span>
      </span>
    </span>
  );
}
