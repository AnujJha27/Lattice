"use client";

import { Camera, Trash2 } from "lucide-react";
import { useRef } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useProfile } from "@/hooks/usePortrait";

type PhotoState = { enabled: boolean; has_photo: boolean };

export function PortraitPhotoSettings() {
  const input = useRef<HTMLInputElement>(null);
  const profile = useProfile();
  const queryClient = useQueryClient();
  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["profile"] });
    void queryClient.invalidateQueries({ queryKey: ["portrait"] });
  };
  const upload = useMutation({
    mutationFn: (file: File) => {
      const body = new FormData();
      body.append("file", file);
      return api<PhotoState>("/users/me/portrait-photo", { method: "POST", body });
    },
    onSuccess: invalidate,
  });
  const toggle = useMutation({
    mutationFn: (enabled: boolean) => api<PhotoState>("/users/me/portrait-photo", {
      method: "PATCH",
      body: JSON.stringify({ enabled }),
    }),
    onSuccess: invalidate,
  });
  const remove = useMutation({
    mutationFn: () => api<PhotoState>("/users/me/portrait-photo", { method: "DELETE" }),
    onSuccess: invalidate,
  });
  const data = profile.data;
  if (!data) return null;
  const error = upload.error ?? toggle.error ?? remove.error;
  return <section className="mt-6 rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6" aria-labelledby="portrait-photo-heading">
    <div className="flex items-start gap-3">
      <Camera className="mt-0.5 h-4 w-4 shrink-0 text-[var(--accent)]" aria-hidden />
      <div className="min-w-0 flex-1">
        <h2 id="portrait-photo-heading" className="text-sm font-semibold">Portrait photo</h2>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-[var(--text-secondary)]">Your photo is optional. It stays private to your account and is used only in the portrait when you turn this on.</p>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <input ref={input} type="file" accept="image/jpeg,image/png,image/webp" className="sr-only" onChange={(event) => { const file = event.target.files?.[0]; if (file) upload.mutate(file); event.currentTarget.value = ""; }} />
          <button type="button" onClick={() => input.current?.click()} disabled={upload.isPending} className="rounded-md border border-[var(--border-subtle)] px-3 py-2 text-xs text-[var(--text-secondary)] hover:border-[var(--accent)] hover:text-[var(--accent)] disabled:opacity-50">{upload.isPending ? "Uploading…" : data.has_portrait_photo ? "Replace photo" : "Choose photo"}</button>
          {data.has_portrait_photo && <label className="inline-flex items-center gap-2 text-xs text-[var(--text-secondary)]"><input type="checkbox" checked={data.portrait_photo_enabled} onChange={(event) => toggle.mutate(event.target.checked)} disabled={toggle.isPending} className="accent-[var(--accent)]" />Use profile photo in portrait</label>}
          {data.has_portrait_photo && <button type="button" onClick={() => remove.mutate()} disabled={remove.isPending} className="inline-flex items-center gap-1.5 text-xs text-[var(--text-muted)] hover:text-[var(--danger)] disabled:opacity-50"><Trash2 className="h-3.5 w-3.5" aria-hidden />Delete photo</button>}
        </div>
        {error && <p role="alert" className="mt-3 text-xs text-[var(--danger)]">{error.message}</p>}
      </div>
    </div>
  </section>;
}
