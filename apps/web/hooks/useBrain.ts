"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { BrainGraph, ConceptDetail } from "@/types/brain";

export function useBrainGraph() {
  return useQuery({
    queryKey: ["brain", "graph"],
    queryFn: () => api<BrainGraph>("/brain/graph"),
  });
}

export function useConceptDetail(conceptId: string | null) {
  return useQuery({
    queryKey: ["concepts", conceptId],
    queryFn: () => api<ConceptDetail>(`/concepts/${conceptId}`),
    enabled: !!conceptId,
  });
}

export function useAddInterest() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { name: string; domain?: string }) =>
      api<{ id: string }>("/concepts", {
        method: "POST",
        body: JSON.stringify({
          canonical_name: input.name,
          domain: input.domain || undefined,
        }),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["brain"] });
    },
  });
}

export function useCombineConcepts() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { concept_a: string; concept_b: string }) =>
      api<{ id: string; canonical_name: string; description: string | null; domain: string | null; difficulty: number | null }>(
        "/concepts/combine",
        { method: "POST", body: JSON.stringify(input) },
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["brain"] });
    },
  });
}
