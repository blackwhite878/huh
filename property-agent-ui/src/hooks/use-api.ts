/**
 * Custom hooks for managing the search pipeline and API interactions
 */

import { useEffect, useCallback } from "react";
import { useAppStore } from "../lib/store";
import { apiClient } from "./api-client";
import type { PropertyResult } from "./types";

/**
 * Hook to manage semantic alignment polling
 */
export function useSemanticAlignment(sessionId: string | null) {
  const { setSemanticTags, setAppState } = useAppStore();

  const pollAlignment = useCallback(async () => {
    if (!sessionId) return;

    try {
      const response = await apiClient.sessionReady(sessionId);

      if (response.status === "ready") {
        setSemanticTags(response.semantic_tags || [], response.alignment_warning || false);
        setAppState("PROFILING_COMPLETE");
        return true;
      }
    } catch (error) {
      console.error("Alignment polling error:", error);
    }
    return false;
  }, [sessionId, setSemanticTags, setAppState]);

  useEffect(() => {
    if (!sessionId) return;

    const handle = setInterval(async () => {
      const done = await pollAlignment();
      if (done) {
        clearInterval(handle);
      }
    }, 3000);

    return () => clearInterval(handle);
  }, [sessionId, pollAlignment]);
}

/**
 * Hook to manage search status polling
 */
export function useSearchStatus(sessionId: string | null) {
  const { setResults, setSearchStage, setAppState } = useAppStore();

  const pollSearch = useCallback(async () => {
    if (!sessionId) return;

    try {
      const response = await apiClient.searchStatus(sessionId);
      setSearchStage(response.status);

      if (response.status === "complete") {
        setResults({
          results: response.results || [],
          batch_index: response.batch_index || 1,
          total_available: response.total_available || 0,
          has_more: response.has_more || false,
          tier3_triggered: response.tier3_triggered || false,
          degraded: response.degraded || false,
        });

        if (response.tier3_triggered) {
          setAppState("TIER3_NO_RESULT");
        } else {
          setAppState("BATCH_1_DISPLAY");
        }

        return true;
      }
    } catch (error) {
      console.error("Search status polling error:", error);
    }
    return false;
  }, [sessionId, setResults, setSearchStage, setAppState]);

  useEffect(() => {
    if (!sessionId) return;

    const handle = setInterval(async () => {
      const done = await pollSearch();
      if (done) {
        clearInterval(handle);
      }
    }, 3000);

    return () => clearInterval(handle);
  }, [sessionId, pollSearch]);
}

/**
 * Hook to handle property rejection
 */
export function usePropertyRejection(sessionId: string | null) {
  const { setRejectionCount } = useAppStore();

  const rejectProperty = useCallback(
    async (propertyId: string, reason: string) => {
      if (!sessionId) return;

      try {
        const response = await apiClient.rejectSingle(sessionId, propertyId, reason);
        setRejectionCount(response.rejection_count);
      } catch (error) {
        console.error("Rejection error:", error);
      }
    },
    [sessionId, setRejectionCount]
  );

  return { rejectProperty };
}

/**
 * Hook to trigger NPP learning and action required flow
 */
export function useNPPLearning(sessionId: string | null) {
  const { setAppState } = useAppStore();

  const triggerNPPLearning = useCallback(async () => {
    if (!sessionId) return;

    try {
      await apiClient.rejectAll(sessionId);
      setAppState("ACTION_REQUIRED_UI");
    } catch (error) {
      console.error("NPP learning error:", error);
    }
  }, [sessionId, setAppState]);

  return { triggerNPPLearning };
}

/**
 * Hook to resolve action required (New Prompt or Keep Memories)
 */
export function useActionResolution(sessionId: string | null) {
  const { setAppState, resetAll, resetForKeepMemories } = useAppStore();

  const resolveAction = useCallback(
    async (action: "new_prompt" | "keep_memories") => {
      if (!sessionId) return;

      try {
        await apiClient.resolveAction(sessionId, action);

        if (action === "new_prompt") {
          resetAll();
          setAppState("PHASE_1_INITIAL");
        } else {
          resetForKeepMemories();
          setAppState("CHATTING");
        }
      } catch (error) {
        console.error("Action resolution error:", error);
      }
    },
    [sessionId, setAppState, resetAll, resetForKeepMemories]
  );

  return { resolveAction };
}

/**
 * Hook to fetch next batch of properties
 */
export function useNextBatch(sessionId: string | null) {
  const { batchIndex, setResults } = useAppStore();

  const fetchNextBatch = useCallback(async () => {
    if (!sessionId) return;

    try {
      const response = await apiClient.nextBatch(sessionId);
      setResults({
        results: response.results,
        batch_index: response.batch_index,
        total_available: response.total_available,
        has_more: response.has_more,
        tier3_triggered: response.tier3_triggered,
        degraded: response.degraded,
      });
    } catch (error) {
      console.error("Next batch error:", error);
    }
  }, [sessionId, setResults]);

  return { fetchNextBatch };
}
