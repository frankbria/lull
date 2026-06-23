// Component catalog for the track builder (US-001).
// ponytail: mobile-local on purpose. The API's COMPONENTS dict
// (apps/api/src/lull_api/scripts.py) defines only 2–3 ids per category; growing it so the
// assembled spec can actually be generated is #13 (Confirm & Generate) / #14 (real LLM).
// Ids reuse the API's where they already exist so that sync is a superset, not a rename.

export type CategoryId = "induction" | "deepener" | "body" | "ending";

export interface ComponentOption {
  id: string;
  name: string;
  blurb: string; // one-line description shown under the name
}

export interface Category {
  id: CategoryId;
  label: string;
  options: ComponentOption[]; // ≥5 per AC
}

export const CATEGORIES: Category[] = [
  {
    id: "induction",
    label: "Induction",
    options: [
      { id: "progressive_relaxation", name: "Progressive relaxation", blurb: "Soften each muscle from head to toe, breath by breath." },
      { id: "fixation", name: "Eye fixation", blurb: "Rest your gaze on a single point and let the edges blur." },
      { id: "breath_counting", name: "Breath counting", blurb: "Count a slow 4-4-6 breath into growing calm." },
      { id: "body_scan", name: "Body scan", blurb: "Sweep attention slowly through the body, releasing tension." },
      { id: "eye_heaviness", name: "Heavy eyelids", blurb: "Let the eyelids grow heavy until they want to close." },
    ],
  },
  {
    id: "deepener",
    label: "Deepener",
    options: [
      { id: "staircase", name: "Staircase", blurb: "Descend a gentle staircase, twice as relaxed each step." },
      { id: "countdown", name: "Countdown", blurb: "Sink deeper with each number from five down to one." },
      { id: "elevator", name: "Elevator", blurb: "Ride a slow elevator down through quiet floors of calm." },
      { id: "deep_breath", name: "Deepening breath", blurb: "Each long exhale carries you further inward." },
      { id: "sinking", name: "Sinking down", blurb: "Settle, heavy and warm, as if into soft sand." },
    ],
  },
  {
    id: "body",
    label: "Body",
    options: [
      { id: "calm_presence", name: "Calm presence", blurb: "Rest in a safe, quiet place with nothing to do." },
      { id: "self_compassion", name: "Self-compassion", blurb: "Let a gentle warmth and kindness grow in your chest." },
      { id: "inner_strength", name: "Inner strength", blurb: "Sense a steady, quiet confidence settling within you." },
      { id: "letting_go", name: "Letting go", blurb: "Release what you've been holding; let it drift away." },
      { id: "healing_light", name: "Healing light", blurb: "A soft light eases through you, soothing as it goes." },
    ],
  },
  {
    id: "ending",
    label: "Ending",
    options: [
      { id: "gentle_emergence", name: "Gentle emergence", blurb: "Count up to five and return rested, clear, awake." },
      { id: "drift_to_sleep", name: "Drift to sleep", blurb: "Let the calm carry you softly down into sleep." },
      { id: "reawaken_energized", name: "Reawaken energized", blurb: "Rise gently, bringing calm energy back with you." },
      { id: "carry_calm", name: "Carry the calm", blurb: "Keep this steadiness with you as the session closes." },
      { id: "peaceful_rest", name: "Peaceful rest", blurb: "Settle into stillness and simply rest a while." },
    ],
  },
];
