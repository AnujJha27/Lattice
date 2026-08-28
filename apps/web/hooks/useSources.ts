"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type {
  DiscoverResponse,
  SourceAcceptPayload,
  SourceItem,
} from "@/types/sources";

export function useDiscover(query: string | null, domain: string | null) {
  return useQuery({
    queryKey: ["sources", "discover", query, domain],
    queryFn: () =>
      api<DiscoverResponse>("/sources/discover", {
        method: "POST",
        body: JSON.stringify({ query, domain: domain || undefined, limit: 10 }),
      }),
    enabled: !!query && query.trim().length >= 3,
    staleTime: 5 * 60_000,
  });
}

export function useLibrary() {
  // Poll while anything is mid-ingest so status badges advance live.
  return useQuery({
    queryKey: ["sources", "library"],
    queryFn: () => api<SourceItem[]>("/sources"),
    refetchInterval: (query) =>
      query.state.data?.some((s) => !["EMBEDDED", "FAILED"].includes(s.ingest_status))
        ? 2_500
        : false,
  });
}

export function useAcceptSource() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: SourceAcceptPayload) =>
      api<SourceItem>("/sources", { method: "POST", body: JSON.stringify(payload) }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["sources"] });
    },
  });
}

export function useRetrySource() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (sourceId: string) =>
      api<SourceItem>(`/sources/${sourceId}/retry`, { method: "POST" }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["sources", "library"] });
    },
  });
}
