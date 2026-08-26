"use client";

import { useRef } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createClient } from "@/lib/supabase/client";
import { PUBLIC_CONFIG } from "@/lib/config";

export function PdfUpload() {
  const input = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();
  const upload = useMutation({
    mutationFn: async (file: File) => {
      const { data } = await createClient().auth.getSession();
      const body = new FormData(); body.append("file", file);
      const response = await fetch(`${PUBLIC_CONFIG.apiUrl}/api/sources/upload`, { method: "POST", headers: data.session?.access_token ? { Authorization: `Bearer ${data.session.access_token}` } : undefined, body });
      if (!response.ok) throw new Error("upload failed");
      return response.json();
    },
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["sources", "library"] }),
  });
  return <div className="mt-3"><input ref={input} type="file" accept="application/pdf,.pdf" className="sr-only" onChange={(e) => { const file = e.target.files?.[0]; if (file) upload.mutate(file); }} /><button type="button" onClick={() => input.current?.click()} disabled={upload.isPending} className="rounded-lg border border-[var(--border-subtle)] px-4 py-2 text-xs font-semibold text-[var(--text-secondary)] hover:border-[var(--accent)] hover:text-[var(--accent)] disabled:opacity-50">{upload.isPending ? "Uploading…" : "Upload PDF"}</button>{upload.isError && <p role="alert" className="mt-2 text-xs text-[var(--danger)]">Couldn&apos;t upload that PDF.</p>}</div>;
}
