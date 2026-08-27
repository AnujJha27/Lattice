"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { trackPortraitEvent } from "@/lib/portraitAnalytics";
import type { PortraitModel } from "@/types/portrait";

type VisualRefreshJob = {
  job_id: string;
  snapshot_id: string;
  status: "PENDING" | "RUNNING" | "SUCCEEDED" | "FAILED" | "CANCELLED";
  portrait?: PortraitModel | null;
  error?: string | null;
};

type PortraitRefreshJob = Omit<VisualRefreshJob, "snapshot_id">;

export function usePortrait() {
  return useQuery({
    queryKey: ["portrait"],
    queryFn: () => api<PortraitModel>("/portrait"),
  });
}

export function usePortraitHistory() {
  return useQuery({
    queryKey: ["portrait", "history"],
    queryFn: () => api<PortraitModel[]>("/portrait/history"),
  });
}

export function useRefreshPortrait() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      let job = await api<PortraitRefreshJob>("/portrait/refresh", { method: "POST" });
      for (let attempt = 0; attempt < 120 && (job.status === "PENDING" || job.status === "RUNNING"); attempt += 1) {
        await new Promise((resolve) => setTimeout(resolve, 1000));
        job = await api<PortraitRefreshJob>(`/portrait/refresh/${job.job_id}`);
      }
      if (job.status !== "SUCCEEDED" || !job.portrait) throw new Error(job.error ?? "Portrait refresh failed");
      return job.portrait;
    },
    onSuccess: (data) => {
      trackPortraitEvent("portrait_refreshed", data.snapshot_id);
      queryClient.setQueryData(["portrait"], data);
      void queryClient.invalidateQueries({ queryKey: ["portrait", "history"] });
    },
  });
}

export function useRefreshPortraitVisuals() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (snapshotId: string) => {
      let job = await api<VisualRefreshJob>(`/portrait/${snapshotId}/visuals/refresh`, { method: "POST" });
      for (let attempt = 0; attempt < 120 && (job.status === "PENDING" || job.status === "RUNNING"); attempt += 1) {
        await new Promise((resolve) => setTimeout(resolve, 1000));
        job = await api<VisualRefreshJob>(`/portrait/${snapshotId}/visuals/refresh/${job.job_id}`);
      }
      if (job.status === "SUCCEEDED" && !job.portrait) {
        job = await api<VisualRefreshJob>(`/portrait/${snapshotId}/visuals/refresh/${job.job_id}`);
      }
      if (job.status !== "SUCCEEDED" || !job.portrait) throw new Error(job.error ?? "Visual refresh failed");
      return job.portrait;
    },
    onSuccess: (data) => {
      trackPortraitEvent("portrait_refreshed", data.snapshot_id);
      queryClient.setQueryData(["portrait"], data);
    },
  });
}
