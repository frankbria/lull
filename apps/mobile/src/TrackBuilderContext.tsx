import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { AI_CHOICE, CATEGORIES, type Category, type CategoryId } from "./catalog";
import { loadHypnosis, saveHypnosis } from "./preferences";

// One selection per category: a concrete option id, or AI_CHOICE meaning "let the AI pick".
// State lives here, above the screen, so selections survive a screen unmount/remount =
// "persists across navigation" (AC). Default is AI_CHOICE for every category, so a first-time
// user starts fully AI-picked (US-002).
export type Selections = Record<CategoryId, string>;

const ALL_AI: Selections = {
  induction: AI_CHOICE,
  deepener: AI_CHOICE,
  body: AI_CHOICE,
  ending: AI_CHOICE,
};

// Picks the concrete option the AI "chooses" for a category. No real LLM yet (#14), so the
// default is a random pick; tests inject a deterministic one.
export type AiPicker = (category: Category) => string;
const randomPick: AiPicker = (c) => c.options[Math.floor(Math.random() * c.options.length)].id;

interface TrackBuilderValue {
  selections: Selections;
  // The AI's concrete pick per category, stable for the provider's lifetime so the preview
  // doesn't change on every render. Revealed in the preview when a category is on AI_CHOICE.
  aiPicks: Selections;
  select: (category: CategoryId, optionId: string) => void; // single-select: replaces prior pick
  // True Hypnosis (true) vs Plain Meditation (false). Persisted, feeds the generation spec (US-003).
  hypnosis: boolean;
  setHypnosis: (value: boolean) => void;
}

const TrackBuilderContext = createContext<TrackBuilderValue | null>(null);

export function TrackBuilderProvider({
  children,
  aiPicker = randomPick,
}: {
  children: ReactNode;
  aiPicker?: AiPicker;
}) {
  const [selections, setSelections] = useState<Selections>(ALL_AI);
  // Computed once (lazy initializer) so the AI's picks stay put across re-renders.
  const [aiPicks] = useState<Selections>(() =>
    Object.fromEntries(CATEGORIES.map((c) => [c.id, aiPicker(c)])) as Selections,
  );
  const select = (category: CategoryId, optionId: string) =>
    setSelections((s) => ({ ...s, [category]: optionId }));

  // Hypnosis-vs-meditation preference: default until the saved value loads on mount, then persist
  // on every change so it's pre-filled next launch (US-003).
  const [hypnosis, setHypnosisState] = useState(true); // True Hypnosis is the first-time default.
  // Set once the user picks, so a slow load can't clobber a choice made before it resolved.
  const userSetRef = useRef(false);
  useEffect(() => {
    let active = true;
    // Apply the stored value only if it exists (non-null) and the user hasn't already chosen.
    loadHypnosis().then((v) => {
      if (active && v !== null && !userSetRef.current) setHypnosisState(v);
    });
    return () => {
      active = false;
    };
  }, []);
  const setHypnosis = (value: boolean) => {
    userSetRef.current = true;
    setHypnosisState(value);
    void saveHypnosis(value);
  };

  return (
    <TrackBuilderContext.Provider
      value={{ selections, aiPicks, select, hypnosis, setHypnosis }}
    >
      {children}
    </TrackBuilderContext.Provider>
  );
}

export function useTrackBuilder(): TrackBuilderValue {
  const ctx = useContext(TrackBuilderContext);
  if (!ctx) throw new Error("useTrackBuilder must be used within a TrackBuilderProvider");
  return ctx;
}
