"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api";
import { nextReviewIndex } from "@/lib/reviewSession";

type Review = { concept_id: string; name: string; mastery_score: number; next_review_at: string | null };
type Quiz = { id: string; question: string; options: string[] };
type QuizResult = { correct: boolean; rationale: string; next_review_at?: string | null };

export default function ReviewPage() {
  const queryClient = useQueryClient();
  const due = useQuery({ queryKey: ["reviews", "due"], queryFn: () => api<Review[]>("/reviews/due") });
  const [queue, setQueue] = useState<Review[]>([]);
  const [activeIndex, setActiveIndex] = useState<number | null>(null);
  const [quiz, setQuiz] = useState<Quiz | null>(null);
  const [result, setResult] = useState<QuizResult | null>(null);
  const [completed, setCompleted] = useState(false);

  const startQuiz = useMutation({
    mutationFn: (conceptId: string) => api<Quiz>(`/concepts/${conceptId}/quiz`, { method: "POST" }),
    onSuccess: (data) => { setQuiz(data); setResult(null); },
  });
  const answer = useMutation({
    mutationFn: ({ quizId, choice }: { quizId: string; choice: number }) =>
      api<QuizResult>(`/quizzes/${quizId}/attempts`, {
        method: "POST",
        body: JSON.stringify({ answer: choice, confidence: 3 }),
      }),
    onSuccess: (data) => {
      setResult(data);
      void queryClient.invalidateQueries({ queryKey: ["reviews", "due"] });
      void queryClient.invalidateQueries({ queryKey: ["brain"] });
      void queryClient.invalidateQueries({ queryKey: ["recommendations"] });
    },
  });

  const active = activeIndex === null ? null : queue[activeIndex];
  const begin = (index: number) => {
    const items = due.data ?? [];
    const item = items[index];
    if (!item) return;
    setQueue(items);
    setActiveIndex(index);
    setCompleted(false);
    setQuiz(null);
    setResult(null);
    startQuiz.mutate(item.concept_id);
  };
  const advance = () => {
    if (activeIndex === null) return;
    const next = nextReviewIndex(activeIndex, queue.length);
    if (next === null) {
      setQueue([]);
      setActiveIndex(null);
      setQuiz(null);
      setResult(null);
      setCompleted(true);
      return;
    }
    setActiveIndex(next);
    setQuiz(null);
    setResult(null);
    startQuiz.mutate(queue[next]!.concept_id);
  };

  return (
    <div className="mx-auto max-w-2xl p-4 sm:p-6 lg:p-14">
      <p className="eyebrow mb-3">Spaced review</p>
      <h1 className="atlas-title text-4xl">Keep the lattice alive.</h1>
      <p className="mt-2 text-sm text-[var(--text-secondary)]">Review what is due; your next interval adapts to each answer.</p>

      {due.isError && <div className="mt-8 rounded-xl border border-[var(--danger)] p-5 text-sm text-[var(--danger)]" role="alert"><p>Couldn&apos;t find your review queue.</p><button onClick={() => void due.refetch()} className="mt-2 underline underline-offset-4">Try again</button></div>}
      {due.isPending && <p className="mt-8 text-sm text-[var(--text-secondary)]" aria-busy="true">Finding due concepts…</p>}

      {completed && <section className="mt-8 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6" aria-live="polite"><p className="eyebrow mb-3">Session complete</p><h2 className="atlas-title text-2xl">That&apos;s the constellation held.</h2><p className="mt-2 text-sm text-[var(--text-secondary)]">Your answers were recorded and the next intervals are scheduled.</p></section>}

      {!active && !completed && due.data?.length === 0 && <p className="mt-8 rounded-xl border border-[var(--border-subtle)] p-5 text-sm text-[var(--text-secondary)]">Nothing due right now. Learn a concept, then return when it is ready for review.</p>}

      {active && <section className="mt-8 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-5" aria-live="polite">
        <div className="mb-6 flex items-center justify-between gap-4"><p className="eyebrow">Review {activeIndex! + 1} of {queue.length}</p><p className="font-mono text-[10px] text-[var(--text-muted)]">{Math.round(active.mastery_score)}% mastery</p></div>
        <h2 className="atlas-title text-2xl">{active.name}</h2>
        {startQuiz.isPending && <p className="mt-5 text-sm text-[var(--text-secondary)]" aria-busy="true">Preparing a question…</p>}
        {startQuiz.isError && <div className="mt-5 text-sm text-[var(--danger)]" role="alert"><p>Couldn&apos;t prepare this question.</p><button onClick={() => startQuiz.mutate(active.concept_id)} className="mt-2 underline underline-offset-4">Try again</button></div>}
        {answer.isError && <p className="mt-5 text-sm text-[var(--danger)]" role="alert">Couldn&apos;t record that answer. Choose again to retry.</p>}
        {quiz && !result && <div className="mt-6"><p className="text-sm font-medium leading-6">{quiz.question}</p><div className="mt-4 space-y-2">{quiz.options.map((option, index) => <button key={`${quiz.id}-${index}`} type="button" disabled={answer.isPending} onClick={() => answer.mutate({ quizId: quiz.id, choice: index })} className="block w-full rounded-md border border-[var(--border-subtle)] px-3 py-3 text-left text-xs transition-colors hover:border-[var(--accent)] disabled:opacity-50">{option}</button>)}</div></div>}
        {result && <div className="mt-6 border-t border-[var(--border-subtle)] pt-5"><p className="text-sm font-semibold">{result.correct ? "Correct." : "Not quite."}</p><p className="mt-2 text-sm leading-6 text-[var(--text-secondary)]">{result.rationale}</p>{result.next_review_at && <p className="mt-3 font-mono text-[10px] uppercase tracking-wider text-[var(--accent)]">Next review · {new Date(result.next_review_at).toLocaleDateString()}</p>}<button type="button" onClick={advance} className="btn-brass mt-5 rounded-md px-4 py-2.5 text-xs font-semibold">{nextReviewIndex(activeIndex!, queue.length) === null ? "Finish review" : "Next concept →"}</button></div>}
      </section>}

      {!active && !completed && due.data && due.data.length > 0 && <div className="mt-8 space-y-3">{due.data.map((item, index) => <article key={item.concept_id} className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-5"><div className="flex items-center justify-between gap-4"><div><h2 className="font-semibold">{item.name}</h2><p className="mt-1 text-xs text-[var(--text-secondary)]">{Math.round(item.mastery_score)}% mastery</p></div><button type="button" onClick={() => begin(index)} className="btn-brass rounded-md px-3 py-2 text-xs font-semibold">Start review</button></div></article>)}</div>}
    </div>
  );
}
