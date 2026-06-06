import type { Metadata } from "next";
import "./globals.css";
import { SessionProvider } from "@/components/SessionProvider";

export const metadata: Metadata = {
  title: "Lexis — Adaptive Book Learning",
  description: "Learn any book with AI-powered spaced repetition and Socratic tutoring.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full bg-slate-50 text-slate-900">
        <SessionProvider>{children}</SessionProvider>
      </body>
    </html>
  );
}
