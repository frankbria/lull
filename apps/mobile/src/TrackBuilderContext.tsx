import { createContext, useContext, useState, type ReactNode } from "react";
import type { CategoryId } from "./catalog";

// One chosen option id per category (null = not yet chosen). State lives here, above the
// screen, so selections survive a screen unmount/remount = "persists across navigation" (AC).
export type Selections = Record<CategoryId, string | null>;

const EMPTY: Selections = { induction: null, deepener: null, body: null, ending: null };

interface TrackBuilderValue {
  selections: Selections;
  select: (category: CategoryId, optionId: string) => void; // single-select: replaces prior pick
}

const TrackBuilderContext = createContext<TrackBuilderValue | null>(null);

export function TrackBuilderProvider({ children }: { children: ReactNode }) {
  const [selections, setSelections] = useState<Selections>(EMPTY);
  const select = (category: CategoryId, optionId: string) =>
    setSelections((s) => ({ ...s, [category]: optionId }));
  return (
    <TrackBuilderContext.Provider value={{ selections, select }}>
      {children}
    </TrackBuilderContext.Provider>
  );
}

export function useTrackBuilder(): TrackBuilderValue {
  const ctx = useContext(TrackBuilderContext);
  if (!ctx) throw new Error("useTrackBuilder must be used within a TrackBuilderProvider");
  return ctx;
}
