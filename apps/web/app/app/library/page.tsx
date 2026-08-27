"use client";

import { Library } from "lucide-react";
import { DiscoverySearch } from "@/components/sources/DiscoverySearch";
import { Reveal } from "@/components/ui/effects";
import { SourceLibraryList } from "@/components/sources/SourceLibraryList";
import { NoteForm } from "@/components/sources/NoteForm";
import { PdfUpload } from "@/components/sources/PdfUpload";

export default function LibraryPage() {
  return (
    <div className="relative h-screen overflow-y-auto">
      <div className="relative mx-auto max-w-5xl p-4 sm:p-6 lg:p-14">
      <header className="mb-10">
        <p className="eyebrow mb-3">
          <Library className="h-3.5 w-3.5" aria-hidden /> Research library
        </p>
        <h1 className="atlas-title text-3xl leading-tight">Sources, not hallucinations.</h1>
        <p className="mx-auto mt-3 max-w-xl text-center text-sm leading-relaxed text-[var(--text-secondary)]">
          Lessons are built from what you save here. Academic and official sources rank first;
          every saved source is fetched, chunked, and embedded so it can ground explanations
          with real citations.
        </p>
      </header>

      <div className="grid max-w-5xl gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <section className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6 shadow-[var(--shadow-md)]">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
            Discover sources
          </h2>
          <DiscoverySearch />
          <div className="mt-6 border-t border-[var(--border-subtle)] pt-5">
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-[var(--text-secondary)]">Add notes or transcript</h2>
            <NoteForm />
            <PdfUpload />
          </div>
        </section>

        <section className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6 shadow-[var(--shadow-md)]">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
            Saved sources
          </h2>
          <SourceLibraryList />
        </section>
      </div>
      </div>
    </div>
  );
}
