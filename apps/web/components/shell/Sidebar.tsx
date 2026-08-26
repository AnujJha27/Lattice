"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LogOut, Brain, Compass, Home, Library, Repeat, Route, Sparkles } from "lucide-react";
import { createClient } from "@/lib/supabase/client";


const NAV = [
  { href: "/app", label: "Overview", icon: Home },
  { href: "/app/brain", label: "Brain", icon: Brain },
  { href: "/app/pathways", label: "Pathways", icon: Route },
  { href: "/app/library", label: "Library", icon: Library },
  { href: "/app/review", label: "Review", icon: Repeat },
  { href: "/app/discovery", label: "Discovery", icon: Compass },
] as const;

export function Sidebar() {
  const router = useRouter();
  const pathname = usePathname();

  async function signOut() {
    await createClient().auth.signOut();
    router.push("/login");
    router.refresh();
  }

  return (
    <aside className="relative z-20 sticky top-0 flex h-screen w-60 shrink-0 self-start flex-col border-r border-[var(--border-subtle)] bg-transparent">
      <div className="relative z-10 flex h-full flex-col p-4">
        <Link href="/app" className="mb-1 block px-2 pt-2">
          <span className="atlas-title bg-gradient-to-br from-[var(--text-primary)] via-[var(--accent)] to-[var(--text-primary)] bg-clip-text text-2xl text-transparent">
            Lattice
          </span>
        </Link>
        <p className="eyebrow mb-8 flex items-center gap-1.5 px-2">
          <Sparkles className="h-3 w-3 text-[var(--accent)]" aria-hidden />
          Observatory
        </p>

        <nav className="flex-1 space-y-0.5" aria-label="Primary">
          {NAV.map(({ href, label, icon: Icon, ...rest }) => {
            const active = pathname === href || (href !== "/app" && pathname.startsWith(href));
            if ("soon" in rest && rest.soon) {
              return (
                <span
                  key={href}
                  title="Coming in a later phase"
                  aria-disabled
                  className="flex cursor-not-allowed items-center gap-2.5 rounded-md px-3 py-2 text-sm text-[var(--text-muted)]"
                >
                  <Icon className="h-4 w-4" aria-hidden />
                  {label}
                  <span className="ml-auto font-mono text-[9px] uppercase tracking-widest opacity-60">soon</span>
                </span>
              );
            }
            return (
              <Link
                key={href}
                href={href}
                aria-current={active ? "page" : undefined}
                className={`group relative flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-all duration-[var(--duration-fast)] ${
                  active
                    ? "bg-[var(--accent-muted)] font-medium text-[var(--accent)]"
                    : "text-[var(--text-secondary)] hover:bg-[var(--bg-raised)]/80 hover:text-[var(--text-primary)]"
                }`}
              >
                {active && (
                  <span
                    aria-hidden
                    className="absolute left-0 top-1/2 h-4 w-0.5 -translate-y-1/2 rounded-full bg-[var(--accent)] shadow-[0_0_8px_rgba(201,169,97,0.8)]"
                  />
                )}
                <Icon className={`h-4 w-4 transition-transform duration-[var(--duration-fast)] ${active ? "scale-110" : "group-hover:scale-110"}`} aria-hidden />
                {label}
              </Link>
            );
          })}
        </nav>

        <button
          onClick={signOut}
          className="flex items-center gap-2 rounded-md px-3 py-2 text-sm text-[var(--text-secondary)] transition-colors duration-[var(--duration-fast)] hover:bg-[var(--bg-raised)]/80 hover:text-[var(--text-primary)]"
        >
          <LogOut className="h-4 w-4" aria-hidden />
          Sign out
        </button>
      </div>
    </aside>
  );
}
