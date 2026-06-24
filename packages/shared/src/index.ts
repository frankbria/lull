// Shared contract types between mobile client and API. Keep in sync with apps/api ScriptOut.

export type ComponentChoice = string | "ai";

export interface TrackSpec {
  induction: ComponentChoice;
  deepener: ComponentChoice;
  body: ComponentChoice;
  ending: ComponentChoice;
  hypnosis: boolean; // false => plain meditation
}

export interface ScriptResponse {
  script: string;
  char_count: number;
  est_seconds: number;
  est_cost_usd: number;
  components: Record<string, string>; // resolved choices (reveals "ai" picks)
}

export const DEFAULT_SPEC: TrackSpec = {
  induction: "ai",
  deepener: "ai",
  body: "ai",
  ending: "ai",
  hypnosis: true,
};

// Voice persona (US-005/FR-V1): a name + descriptor the user picks from. The raw ElevenLabs
// voice id stays server-side (apps/api personas.py) so the underlying voice can be swapped
// without breaking saved preferences — same client/server catalog split as the component catalog
// (mobile catalog.ts <-> api scripts.py). Keep these ids in sync with PERSONA_VOICE_IDS.
export interface VoicePersona {
  id: string;
  name: string;
  descriptor: string;
}

export const VOICE_PERSONAS: VoicePersona[] = [
  { id: "aria", name: "Aria", descriptor: "Warm and soothing — a gentle evening calm" },
  { id: "sarah", name: "Sarah", descriptor: "Reassuring and steady — grounded and clear" },
  { id: "charlotte", name: "Charlotte", descriptor: "Soft and dreamy — airy and light" },
  { id: "james", name: "James", descriptor: "Deep and grounding — slow and steady" },
  { id: "daniel", name: "Daniel", descriptor: "Low and resonant — a calm, sure presence" },
  { id: "lily", name: "Lily", descriptor: "Bright and tender — nurturing warmth" },
];

export const DEFAULT_VOICE_ID = VOICE_PERSONAS[0].id;
