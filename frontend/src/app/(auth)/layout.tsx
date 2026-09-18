import Link from "next/link";

import { Logo } from "@/components/landing";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-grain-fade">
      <header className="container-page flex h-16 items-center">
        <Link href="/" className="flex items-center gap-2.5">
          <Logo />
          <span className="font-display text-lg text-slatey-100">FilmFund Africa</span>
        </Link>
      </header>

      <main className="container-page flex flex-1 items-center justify-center py-12">
        <div className="w-full max-w-md animate-fade-up">{children}</div>
      </main>

      <footer className="container-page py-6 text-center text-xs text-slatey-500">
        De l&apos;idée au financement de votre projet audiovisuel.
      </footer>
    </div>
  );
}
