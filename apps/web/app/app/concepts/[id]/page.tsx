"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { AlertTriangle, ArrowLeft, BookOpen, ChevronLeft, ChevronRight, ExternalLink, RefreshCw } from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { CitedParagraph } from "@/components/lessons/CitationMarker";
import { useConcept, useGenerateLesson, useLesson } from "@/hooks/useLesson";
import { MASTERY_COLORS } from "@/types/brain";

const GROUNDING_LABELS: Record<string, string> = {
  GROUNDED: "Fully grounded in your sources",
  MIXED: "Mix of cited sources and explanation",
  GENERATED: "AI explanation — no source coverage found",
};

const GENERATION_STAGES = [
  "Finding relevant sources",
  "Building lesson context",
  "Writing the chapter",
  "Checking citations",
];

export default function ConceptPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const concept = useConcept(id);
  const [queued, setQueued] = useState(false);
  const [generationStage, setGenerationStage] = useState(0);
  const lesson = useLesson(id, queued);
  const generate = useGenerateLesson(id);

  useEffect(() => {
    if (lesson.data) setQueued(false);
  }, [lesson.data]);

  const isGenerating = queued || generate.isPending;

  useEffect(() => {
    if (!isGenerating) {
      setGenerationStage(0);
      return;
    }
    const timer = setInterval(() => {
      setGenerationStage((stage) => (stage + 1) % GENERATION_STAGES.length);
    }, 4_000);
    return () => clearInterval(timer);
  }, [isGenerating]);

  const showLesson = lesson.data?.content?.intuition !== undefined ? lesson.data : undefined;
  const noLessonYet = !lesson.data && !isGenerating;
  const [activeSection, setActiveSection] = useState(0);
  const sections = showLesson?.content.sections ?? [];
  const hasSections = sections.length > 0;

  // reset stepper when lesson changes
  useEffect(() => {
    setActiveSection(0);
  }, [showLesson?.generated_at]);

  return (
    <div className="relative min-h-screen">
      <div className="relative mx-auto max-w-3xl p-8 lg:p-14">
        <Link
          href="/app/pathways"
          className="mb-6 inline-flex items-center gap-1.5 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden /> Back
        </Link>

        {/* Header */}
        <header className="mb-8">
          <h1 className="atlas-title text-3xl">
            {concept.data?.canonical_name ?? "Loading…"}
          </h1>
          <p className="mt-1 text-xs uppercase tracking-wider text-[var(--text-muted)]">
            {concept.data?.domain ?? ""}
          </p>
          {concept.data && (
            <div
              role="progressbar"
              aria-valuenow={Math.round(concept.data.mastery_score)}
              aria-valuemin={0}
              aria-valuemax={100}
              className="mt-3 h-1.5 max-w-xs overflow-hidden rounded-full bg-[var(--bg-surface)]"
            >
              <div
                className="h-full rounded-full transition-all duration-[var(--duration-slow)]"
                style={{
                  width: `${Math.max(concept.data.mastery_score, 2)}%`,
                  background: MASTERY_COLORS[concept.data.state],
                }}
              />
            </div>
          )}
        </header>

        {/* Generating state */}
        {isGenerating && (
          <div className="flex flex-col items-center py-20 text-center" role="status" aria-busy="true">
            <div className="relative mb-6 h-16 w-16">
              <div className="absolute inset-0 rounded-full border border-[var(--border-subtle)]" />
              <motion.div
                className="absolute inset-0"
                animate={{ rotate: 360 }}
                transition={{ duration: 3.2, repeat: Infinity, ease: "linear" }}
              >
                <span
                  aria-hidden
                  className="absolute left-1/2 top-0 h-2 w-2 -translate-x-1/2 -translate-y-1/2 rounded-full bg-[var(--accent)] shadow-[0_0_10px_rgba(201,169,97,0.9)]"
                />
              </motion.div>
              <div className="absolute inset-0 flex items-center justify-center">
                <BookOpen className="h-5 w-5 text-[var(--accent)]" aria-hidden />
              </div>
            </div>
            <p className="atlas-title text-xl">Building your grounded lesson</p>
            <p className="mt-2 max-w-sm text-sm leading-relaxed text-[var(--text-secondary)]">
              Gathering source excerpts and writing an explanation that cites them.
              This takes 1–3 minutes for a full chapter.
            </p>
            <p className="mt-4 font-mono text-[10px] uppercase tracking-widest text-[var(--accent)]" aria-live="polite">
              {GENERATION_STAGES[generationStage]}
            </p>
            <div className="mt-6 h-1 w-56 overflow-hidden rounded-full bg-[var(--bg-raised)]">
              <motion.div
                className="h-full w-2/5 rounded-full bg-gradient-to-r from-transparent via-[var(--accent)] to-transparent"
                animate={{ x: ["-120%", "320%"] }}
                transition={{ duration: 1.8, repeat: Infinity, ease: [0.45, 0, 0.55, 1] }}
              />
            </div>
          </div>
        )}

        {/* No lesson yet */}
        {noLessonYet && !isGenerating && (
          <div className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)]/80 backdrop-blur p-8 text-center">
            <h2 className="mb-2 font-medium">No lesson yet</h2>
            <p className="mx-auto mb-6 max-w-sm text-sm leading-relaxed text-[var(--text-secondary)]">
              Generate a grounded lesson: Lattice finds relevant excerpts from your
              saved sources (discovering new ones if needed) and writes a
              chapter citing exactly those.
            </p>
            <button
              onClick={async () => {
                await generate.mutateAsync();
                setQueued(true);
              }}
              disabled={concept.isPending}
              className="btn-brass rounded-lg px-5 py-2.5 text-sm font-semibold disabled:opacity-50"
            >
              Generate grounded lesson
            </button>
          </div>
        )}

        {/* Lesson body */}
        {showLesson && showLesson.content && (
          <article className="space-y-8">
            <div
              className={`inline-flex rounded-full px-3 py-1 text-[10px] font-semibold uppercase tracking-wide ${
                showLesson.grounding === "GENERATED"
                  ? "bg-[rgba(251,191,36,0.12)] text-[var(--warning)]"
                  : "bg-[rgba(74,222,128,0.12)] text-[var(--success)]"
              }`}
              title={GROUNDING_LABELS[showLesson.grounding]}
            >
              {GROUNDING_LABELS[showLesson.grounding]}
            </div>

            <section>
              <h2 className="mb-2 text-xs font-semibold uppercase tracking-wider text-[var(--accent)]">
                The core idea
              </h2>
              <p className="font-[var(--font-display)] text-[17px] leading-8 text-[var(--text-primary)] italic">
                <span className="float-left mr-2 mt-1 font-[var(--font-display)] text-4xl leading-none text-[var(--accent)]">
                  {showLesson.content.intuition.trim().charAt(0)}
                </span>
                {showLesson.content.intuition.trim().slice(1)}
              </p>
            </section>

            {hasSections ? (
              <>
                {/* Chapter progress */}
                <div className="sticky top-0 z-10 -mx-8 border-y border-[var(--border-subtle)] bg-[var(--bg-base)]/90 px-8 py-3 backdrop-blur lg:-mx-14 lg:px-14">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[10px] uppercase tracking-widest text-[var(--text-muted)]">
                      {String(activeSection + 1).padStart(2, "0")} / {String(sections.length).padStart(2, "0")}
                    </span>
                    <div className="flex flex-1 gap-1">
                      {sections.map((_, i) => (
                        <button
                          key={i}
                          onClick={() => setActiveSection(i)}
                          aria-label={`Go to section ${i + 1}`}
                          aria-current={i === activeSection ? "step" : undefined}
                          className={`h-1 flex-1 rounded-full transition-colors duration-300 ${
                            i < activeSection
                              ? "bg-[var(--accent)]"
                              : i === activeSection
                                ? "bg-[var(--accent)]"
                                : "bg-[var(--bg-raised)]"
                          }`}
                        />
                      ))}
                    </div>
                    <div className="flex gap-1">
                      <button
                        onClick={() => setActiveSection((s) => Math.max(0, s - 1))}
                        disabled={activeSection === 0}
                        aria-label="Previous section"
                        className="rounded-md border border-[var(--border-subtle)] p-1.5 text-[var(--text-secondary)] hover:text-[var(--text-primary)] disabled:opacity-30"
                      >
                        <ChevronLeft className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => setActiveSection((s) => Math.min(sections.length - 1, s + 1))}
                        disabled={activeSection === sections.length - 1}
                        aria-label="Next section"
                        className="rounded-md border border-[var(--border-subtle)] p-1.5 text-[var(--text-secondary)] hover:text-[var(--text-primary)] disabled:opacity-30"
                      >
                        <ChevronRight className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                  <p className="mt-2 truncate font-mono text-[11px] uppercase tracking-widest text-[var(--accent)]">
                    {sections[activeSection]?.heading}
                  </p>
                </div>

                <AnimatePresence mode="wait">
                  <motion.div
                    key={activeSection}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
                  >
                    {(() => {
                      const section = sections[activeSection]!;
                      const sourcesById = new Map(showLesson.sources.map((src) => [src.index, src]));
                      return (
                        <section>
                          <h2 className="atlas-title mb-4 flex items-baseline gap-3 text-2xl">
                            <span className="font-mono text-xs text-[var(--accent)]">
                              {String(activeSection + 1).padStart(2, "0")}
                            </span>
                            {section.heading}
                          </h2>
                          <div className="space-y-5">
                            {section.paragraphs.map((paragraph, pi) => (
                              <CitedParagraph
                                key={pi}
                                text={paragraph.text}
                                sourceIds={paragraph.source_ids}
                                sourcesByIdIndex={sourcesById}
                                serif
                              />
                            ))}
                          </div>
                          {section.equations && section.equations.length > 0 && (
                            <div className="mt-6 space-y-1.5 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)]/80 p-5 backdrop-blur">
                              {section.equations.map((eq, ei) => (
                                <code
                                  key={ei}
                                  className="block overflow-x-auto py-1 font-mono text-[13px] text-[var(--text-primary)]"
                                >
                                  {eq}
                                </code>
                              ))}
                            </div>
                          )}
                          {section.key_points && section.key_points.length > 0 && (
                            <div className="mt-6 rounded-xl border-l-2 border-[var(--accent)] bg-[var(--accent-muted)]/40 p-5">
                              <p className="eyebrow mb-2">Retain</p>
                              <ul className="space-y-2">
                                {section.key_points.map((point, ki) => (
                                  <li key={ki} className="flex gap-2 text-[13px] leading-6">
                                    <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-[var(--accent)]" />
                                    {point}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                          <div className="mt-8 flex justify-between">
                            <button
                              onClick={() => setActiveSection((s) => Math.max(0, s - 1))}
                              disabled={activeSection === 0}
                              className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--border-subtle)] px-4 py-2 text-xs font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] disabled:opacity-30"
                            >
                              <ChevronLeft className="h-3.5 w-3.5" /> Previous
                            </button>
                            <button
                              onClick={() => setActiveSection((s) => Math.min(sections.length - 1, s + 1))}
                              disabled={activeSection === sections.length - 1}
                              className="btn-brass inline-flex items-center gap-1.5 rounded-lg px-4 py-2 text-xs font-semibold disabled:opacity-50"
                            >
                              Next <ChevronRight className="h-3.5 w-3.5" />
                            </button>
                          </div>
                        </section>
                      );
                    })()}
                  </motion.div>
                </AnimatePresence>
              </>
            ) : (
              <section className="space-y-4">
                {(showLesson.content.paragraphs ?? []).map((paragraph, i) => (
                  <CitedParagraph
                    key={i}
                    text={paragraph.text}
                    sourceIds={paragraph.source_ids}
                    sourcesByIdIndex={new Map(showLesson.sources.map((s) => [s.index, s]))}
                  />
                ))}
              </section>
            )}

            {(showLesson.content.equations ?? []).length > 0 && !hasSections && (
              <section className="space-y-2 rounded-xl bg-[var(--bg-surface)]/80 p-5 backdrop-blur">
                <h2 className="text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
                  Key relations
                </h2>
                {showLesson.content.equations.map((eq, i) => (
                  <code key={i} className="block overflow-x-auto py-1 font-mono text-sm text-[var(--text-primary)]">
                    {eq}
                  </code>
                ))}
              </section>
            )}

            {(showLesson.content.examples ?? []).length > 0 && (
              <section className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)]/60 p-5">
                <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
                  Worked examples
                </h2>
                <ul className="space-y-3">
                  {showLesson.content.examples.map((ex, i) => (
                    <li key={i} className="text-sm leading-7">
                      <span className="mr-2 font-mono text-[10px] text-[var(--accent)]">
                        {String(i + 1).padStart(2, "0")}
                      </span>
                      {ex}
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {(showLesson.content.common_mistakes ?? []).length > 0 && (
              <section className="rounded-xl border border-[rgba(251,191,36,0.2)] bg-[rgba(251,191,36,0.06)] p-5">
                <h2 className="mb-3 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-[var(--warning)]">
                  <AlertTriangle className="h-3.5 w-3.5" aria-hidden /> Common mistakes
                </h2>
                <ul className="space-y-3">
                  {showLesson.content.common_mistakes.map((m, i) => (
                    <li key={i} className="text-sm leading-7">{m}</li>
                  ))}
                </ul>
              </section>
            )}

            {(showLesson.sources ?? []).length > 0 && (
              <section className="border-t border-[var(--border-subtle)] pt-8">
                <h2 className="mb-4 text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
                  Sources ({showLesson.sources.length})
                </h2>
                <ul className="grid gap-2 sm:grid-cols-2">
                  {showLesson.sources.map((source, i) => (
                    <li key={source.source_id}>
                      <a
                        href={source.url ?? "#"}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex h-full items-start gap-2.5 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-3.5 transition-colors duration-[var(--duration-fast)] hover:border-[var(--accent)]"
                      >
                        <span className="mt-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-[var(--accent-muted)] px-1 text-[9px] font-bold text-[var(--accent)]">
                          {i + 1}
                        </span>
                        <span className="min-w-0">
                          <span className="block truncate text-xs font-medium">{source.title}</span>
                          <span className="block truncate text-[10px] text-[var(--text-muted)]">
                            {[...source.authors.slice(0, 2), source.publisher].filter(Boolean).join(" · ")}
                          </span>
                        </span>
                        <ExternalLink className="ml-auto mt-0.5 h-3 w-3 shrink-0 text-[var(--text-muted)]" aria-hidden />
                      </a>
                    </li>
                  ))}
                </ul>
              </section>
            )}

            <QuizCard conceptId={id} />

            <footer className="flex flex-wrap gap-2 border-t border-[var(--border-subtle)] pt-6">
              <button
                onClick={async () => {
                  await generate.mutateAsync();
                  setQueued(true);
                }}
                disabled={generate.isPending || queued}
                className="flex items-center gap-2 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-4 py-2 text-xs font-medium text-[var(--text-secondary)] transition-colors hover:border-[var(--border-strong)] hover:text-[var(--text-primary)] disabled:opacity-50"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${generate.isPending ? "animate-spin" : ""}`} aria-hidden />
                Regenerate
              </button>
            </footer>
          </article>
        )}
      </div>
    </div>
  );
}

type QuizResponse = { id: string; question: string; options: string[] };
type QuizResult = { correct: boolean; rationale: string; next_review_at?: string | null };

function QuizCard({ conceptId }: { conceptId: string }) {
  const queryClient = useQueryClient();
  const [quiz, setQuiz] = useState<QuizResponse | null>(null);
  const [result, setResult] = useState<QuizResult | null>(null);
  const start = useMutation({ mutationFn: () => api<QuizResponse>(`/concepts/${conceptId}/quiz`, { method: "POST" }), onSuccess: (data) => { setQuiz(data); setResult(null); } });
  const answer = useMutation({ mutationFn: (choice: number) => api<QuizResult>(`/quizzes/${quiz!.id}/answer`, { method: "POST", body: JSON.stringify({ answer: choice }) }), onSuccess: (data) => { setResult(data); void queryClient.invalidateQueries({ queryKey: ["brain"] }); void queryClient.invalidateQueries({ queryKey: ["concepts", conceptId] }); void queryClient.invalidateQueries({ queryKey: ["recommendations"] }); } });
  if (!quiz) return <button onClick={() => start.mutate()} disabled={start.isPending} className="rounded-lg border border-[var(--border-subtle)] px-4 py-2 text-xs font-medium text-[var(--text-secondary)]">{start.isPending ? "Preparing quiz…" : "Quiz me →"}</button>;
  return <section className="mb-6 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-5"><p className="eyebrow mb-3">Quick check</p><h2 className="mb-4 text-sm font-semibold">{quiz.question}</h2><div className="space-y-2">{quiz.options.map((option, i) => <button key={`${quiz.id}-${i}`} disabled={answer.isPending || !!result} onClick={() => answer.mutate(i)} className="block w-full rounded-md border border-[var(--border-subtle)] px-3 py-2 text-left text-xs hover:border-[var(--accent)]">{option}</button>)}</div>{result && <div className="mt-4 text-xs text-[var(--text-secondary)]"><p>{result.correct ? "Correct." : "Not quite."} {result.rationale}</p><button className="mt-3 text-[var(--accent)] hover:underline" onClick={() => { setQuiz(null); setResult(null); }}>Try another question</button></div>}</section>;
}
