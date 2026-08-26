"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { ConceptDetail } from "@/types/brain";
import type { Lesson } from "@/types/lessons";

export function useConcept(conceptId: string | null) {
  return useQuery({
    queryKey: ["concepts", conceptId],
    queryFn: () => api<ConceptDetail>(`/concepts/${conceptId}`),
    enabled: !!conceptId,
  });
}

export function useLesson(conceptId: string, pollWhileQueued = false) {
  return useQuery({
    queryKey: ["lessons", conceptId],
    queryFn: () => api<Lesson>(`/concepts/${conceptId}/lesson`),
    retry: false,
    // While a generation job runs, poll until the lesson lands.
    refetchInterval: pollWhileQueued ? 3_000 : false,
  });
}

export function useGenerateLesson(conceptId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      api<{ status: string }>(`/concepts/${conceptId}/lesson`, { method: "POST" }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["brain"] });
      void queryClient.invalidateQueries({ queryKey: ["pathways"] });
    },
  });
}
