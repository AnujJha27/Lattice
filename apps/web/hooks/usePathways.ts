"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { PathwayDetail, PathwaySummary } from "@/types/pathways";

export function usePathways() {
  // Keep polling while any pathway is still generating.
  return useQuery({
    queryKey: ["pathways"],
    queryFn: () => api<PathwaySummary[]>("/pathways"),
    refetchInterval: (query) =>
      query.state.data?.some((p) => p.status === "GENERATING") ? 2_500 : false,
  });
}

export function usePathway(id: string | null) {
  return useQuery({
    queryKey: ["pathways", id],
    queryFn: () => api<PathwayDetail>(`/pathways/${id}`),
    enabled: !!id,
    refetchInterval: (query) =>
      query.state.data?.status === "GENERATING" ? 2_500 : false,
  });
}

export function useCreatePathway() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { topic: string; target_depth: "beginner" | "intermediate" | "advanced" }) =>
      api<PathwaySummary>("/pathways", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["pathways"] });
    },
  });
}

export function useDeletePathway() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api<void>(`/pathways/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["pathways"] });
      void queryClient.invalidateQueries({ queryKey: ["brain"] });
    },
  });
}
