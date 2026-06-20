import { create } from "zustand";

type ProjectState = {
  currentProjectId: string | null;
  setCurrentProjectId: (id: string | null) => void;
};

export const useProjectStore = create<ProjectState>((set) => ({
  currentProjectId: null,
  setCurrentProjectId: (id) => set({ currentProjectId: id })
}));
