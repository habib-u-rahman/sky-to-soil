import { CtaSection } from "@/components/landing/cta-section";
import { Hero } from "@/components/landing/hero";
import { HowItWorks } from "@/components/landing/how-it-works";
import { NasaDataSection } from "@/components/landing/nasa-data-section";

export default function HomePage() {
  return (
    <>
      <Hero />
      <HowItWorks />
      <NasaDataSection />
      <CtaSection />
    </>
  );
}
