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
