import { useEffect, useRef } from 'react';
import { gsap, prefersReducedMotion } from '../../lib/gsap';

/**
 * Image avec parallaxe verticale subtile.
 * Le parent doit gérer le débordement et le ratio.
 */
export default function ParallaxImage({
  src,
  alt,
  className = '',
  imgClassName = '',
  speed = 6,
  eager = false,
}) {
  const wrapperRef = useRef(null);
  const imageRef = useRef(null);

  useEffect(() => {
    if (prefersReducedMotion()) return undefined;

    const ctx = gsap.context(() => {
      gsap.fromTo(
        imageRef.current,
        { yPercent: -speed },
        {
          yPercent: speed,
          ease: 'none',
          scrollTrigger: {
            trigger: wrapperRef.current,
            start: 'top bottom',
            end: 'bottom top',
            scrub: 0.6,
          },
        }
      );
    }, wrapperRef);

    return () => ctx.revert();
  }, [speed]);

  return (
    <div ref={wrapperRef} className={`overflow-hidden ${className}`}>
      <img
        ref={imageRef}
        src={src}
        alt={alt}
        loading={eager ? 'eager' : 'lazy'}
        decoding="async"
        className={`h-full w-full scale-[1.15] object-cover ${imgClassName}`}
      />
    </div>
  );
}
