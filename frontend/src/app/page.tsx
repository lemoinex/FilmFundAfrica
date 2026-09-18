import {
  AiWriter,
  Audiences,
  BudgetSection,
  Faq,
  FinalCta,
  Funding,
  Hero,
  LandingFooter,
  LandingNav,
  Pricing,
  Problem,
  Solution,
} from "@/components/landing";

export default function LandingPage() {
  return (
    <>
      <LandingNav />
      <main>
        <Hero />
        <Problem />
        <Solution />
        <AiWriter />
        <Funding />
        <BudgetSection />
        <Audiences />
        <Pricing />
        <Faq />
        <FinalCta />
      </main>
      <LandingFooter />
    </>
  );
}
