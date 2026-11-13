import { useCallback, useState } from 'react';
import FomoBar from './components/layout/FomoBar';
import Header from './components/layout/Header';
import Footer from './components/layout/Footer';
import StickyWhatsApp from './components/layout/StickyWhatsApp';
import Hero from './components/sections/Hero';
import Marquee from './components/sections/Marquee';
import TrustStats from './components/sections/TrustStats';
import Cabinet from './components/sections/Cabinet';
import Services from './components/sections/Services';
import Technology from './components/sections/Technology';
import Faq from './components/sections/Faq';
import Contact from './components/sections/Contact';
import BookingModal from './components/booking/BookingModal';
import { useSmoothScroll } from './hooks/useSmoothScroll';
import { useScrollReveal } from './hooks/useScrollReveal';

export default function App() {
  const [bookingOpen, setBookingOpen] = useState(false);
  const [initialTreatment, setInitialTreatment] = useState(null);

  useSmoothScroll();
  useScrollReveal();

  const openBooking = useCallback((treatment = null) => {
    setInitialTreatment(treatment);
    setBookingOpen(true);
  }, []);

  const closeBooking = useCallback(() => setBookingOpen(false), []);

  return (
    <div className="grain min-h-screen bg-orbit-bg text-orbit-ink">
      <a
        href="#accueil"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-[120] focus:rounded-full focus:bg-orbit-ink focus:px-5 focus:py-3 focus:text-xs focus:font-bold focus:uppercase focus:tracking-[0.14em] focus:text-orbit-bg"
      >
        Aller au contenu
      </a>

      <FomoBar onBook={() => openBooking()} />
      <Header onBook={() => openBooking()} />

      <main>
        <Hero onBook={() => openBooking()} />
        <Marquee />
        <TrustStats />
        <Cabinet />
        <Services onBook={openBooking} />
        <Technology />
        <Faq />
        <Contact onBook={() => openBooking()} />
      </main>

      <Footer onBook={() => openBooking()} />
      <StickyWhatsApp />

      <BookingModal
        open={bookingOpen}
        initialTreatment={initialTreatment}
        onClose={closeBooking}
      />
    </div>
  );
}
