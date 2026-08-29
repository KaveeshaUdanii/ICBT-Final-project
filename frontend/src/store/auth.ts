import { create } from "zustand";
import type { User } from "../types";

interface AuthState {
  token: string | null;
  user: User | null;
  setAuth: (token: string, user: User) => void;
  clearAuth: () => void;
}

// Deliberately not persisted to localStorage: every fresh app load (new tab, browser
// restart, hard refresh) should land on the login screen rather than silently resuming a
// prior session. setAuth/clearAuth only affect in-memory state for the current page load.
export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  user: null,
  setAuth: (token, user) => set({ token, user }),
  clearAuth: () => set({ token: null, user: null }),
}));
