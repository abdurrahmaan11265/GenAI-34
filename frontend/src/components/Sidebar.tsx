"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Library, BookOpen, BarChart2, User, BrainCircuit } from "lucide-react";
import { cn } from "@/lib/utils";

const nav = [
  { href: "/library", icon: Library, label: "Library" },
  { href: "/progress", icon: BarChart2, label: "Progress" },
  { href: "/settings", icon: User, label: "Profile" },
];

export function Sidebar() {
  const path = usePathname();
  return (
    <aside className="fixed left-0 top-0 h-full w-16 lg:w-56 bg-white border-r border-slate-200 flex flex-col z-40">
      <div className="flex items-center gap-2 px-4 py-5 border-b border-slate-100">
        <BrainCircuit className="h-7 w-7 text-indigo-600 shrink-0" />
        <span className="hidden lg:block font-bold text-slate-900 text-lg">Lexis</span>
      </div>
      <nav className="flex-1 p-2 space-y-1 mt-2">
        {nav.map(({ href, icon: Icon, label }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
              path.startsWith(href)
                ? "bg-indigo-50 text-indigo-700"
                : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
            )}
          >
            <Icon className="h-5 w-5 shrink-0" />
            <span className="hidden lg:block">{label}</span>
          </Link>
        ))}
      </nav>
    </aside>
  );
}
