import { QueryClient } from "@tanstack/react-query";
import { apiData, apiErrorMessage, apiSucceeded } from "@/shared/lib/api";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      gcTime: 5 * 60_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
    mutations: { retry: 0 },
  },
});

export async function fetchApiQuery<T>(queryKey: readonly unknown[], url: string): Promise<T> {
  return queryClient.fetchQuery({
    queryKey,
    queryFn: async ({ signal }) => {
      const response = await fetch(url, {
        signal,
        cache: "no-store",
        credentials: "same-origin",
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      const json = await response.json().catch(() => ({}));
      if (!apiSucceeded(response, json)) {
        throw new Error(apiErrorMessage(json, "Unable to load data."));
      }
      return apiData<T>(json);
    },
  });
}
