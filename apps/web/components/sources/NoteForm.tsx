"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function NoteForm() {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const save = useMutation({
    mutationFn: () => api("/sources/notes", { method: "POST", body: JSON.stringify({ title, content }) }),
    onSuccess: () => { setTitle(""); setContent(""); void queryClient.invalidateQueries({ queryKey: ["sources", "library"] }); },
  });
  return <form className="space-y-2.5" onSubmit={(event) => { event.preventDefault(); if (title.trim() && content.trim().length >= 20) save.mutate(); }}>
    <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Note or transcript title" aria-label="Note title" className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-base)] px-3.5 py-2 text-sm outline-none focus:border-[var(--accent)]" />
    <textarea value={content} onChange={(e) => setContent(e.target.value)} placeholder="Paste notes, a transcript, or an excerpt…" aria-label="Note content" rows={4} className="w-full resize-y rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-base)] px-3.5 py-2 text-sm outline-none focus:border-[var(--accent)]" />
    <button type="submit" disabled={save.isPending || !title.trim() || content.trim().length < 20} className="rounded-lg border border-[var(--border-subtle)] px-4 py-2 text-xs font-semibold text-[var(--text-secondary)] hover:border-[var(--accent)] hover:text-[var(--accent)] disabled:opacity-50">{save.isPending ? "Saving…" : "Save note"}</button>
    {save.isError && <p role="alert" className="text-xs text-[var(--danger)]">Couldn&apos;t save that note.</p>}
  </form>;
}
