"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

type Review = { concept_id: string; name: string; mastery_score: number; next_review_at: string | null };

export default function ReviewPage() {
  const queryClient = useQueryClient();
  const due = useQuery({ queryKey: ["reviews", "due"], queryFn: () => api<Review[]>("/reviews/due") });
  const submit = useMutation({
    mutationFn: ({ id, correct, confidence }: { id: string; correct: boolean; confidence: number }) =>
      api<Review>(`/concepts/${id}/reviews`, { method: "POST", body: JSON.stringify({ correct, confidence }) }),
    onSuccess: () => { void queryClient.invalidateQueries({ queryKey: ["reviews", "due"] }); void queryClient.invalidateQueries({ queryKey: ["brain"] }); void queryClient.invalidateQueries({ queryKey: ["recommendations"] }); },
  });

  return (
    <div className="mx-auto max-w-2xl p-4 sm:p-6 lg:p-14">
      <p className="eyebrow mb-3">Spaced review</p>
      <h1 className="atlas-title text-4xl">Keep the lattice alive.</h1>
      <p className="mt-2 text-sm text-[var(--text-secondary)]">Review what is due; your next interval adapts to each answer.</p>
      <div className="mt-8 space-y-3">
        {due.isPending && <p className="text-sm text-[var(--text-secondary)]">Finding due concepts…</p>}
        {due.data?.length === 0 && <p className="rounded-xl border border-[var(--border-subtle)] p-5 text-sm text-[var(--text-secondary)]">Nothing due right now. Learn a concept, then return when it is ready for review.</p>}
        {due.data?.map((item) => (
          <article key={item.concept_id} className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-5">
            <h2 className="font-semibold">{item.name}</h2>
            <p className="mt-1 text-xs text-[var(--text-secondary)]">{Math.round(item.mastery_score)}% mastery</p>
            <div className="mt-4 flex gap-2">
              <button disabled={submit.isPending} onClick={() => submit.mutate({ id: item.concept_id, correct: false, confidence: 1 })} className="rounded-md border border-[var(--border-subtle)] px-3 py-2 text-xs text-[var(--text-secondary)]">Need practice</button>
              <button disabled={submit.isPending} onClick={() => submit.mutate({ id: item.concept_id, correct: true, confidence: 4 })} className="btn-brass rounded-md px-3 py-2 text-xs font-semibold">Remembered</button>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
