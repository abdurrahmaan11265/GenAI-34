/**
 * Assessment session state — survives navigation between question pages.
 *
 * The backend manages the topological walk and question generation.
 * This store only tracks what the UI needs client-side:
 *   - which bookId is being assessed
 *   - the running result map (for the results screen)
 *   - how many topics have been completed
 */

import { create } from "zustand";
import type { NodeState } from "@/types/dto";

interface AssessmentResult {
  nodeId: string;
  nodeTitle: string;
  mastered: boolean;
  confidence: string;
}

interface AssessmentState {
  bookId: string | null;
  topicIndex: number;
  totalTopics: number;
  results: AssessmentResult[];

  // Actions
  init: (bookId: string, totalTopics: number) => void;
  recordAnswer: (result: AssessmentResult) => void;
  incrementTopic: () => void;
  reset: () => void;
}

export const useAssessmentStore = create<AssessmentState>((set) => ({
  bookId: null,
  topicIndex: 0,
  totalTopics: 0,
  results: [],

  init(bookId, totalTopics) {
    set({ bookId, topicIndex: 0, totalTopics, results: [] });
  },

  recordAnswer(result) {
    set((s) => ({ results: [...s.results, result] }));
  },

  incrementTopic() {
    set((s) => ({ topicIndex: s.topicIndex + 1 }));
  },

  reset() {
    set({ bookId: null, topicIndex: 0, totalTopics: 0, results: [] });
  },
}));
