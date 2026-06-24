import AsyncStorage from "@react-native-async-storage/async-storage";
import { VOICE_PERSONAS } from "@lull/shared";

// Persisted user preferences. Add more keys here as they appear.
export const HYPNOSIS_KEY = "lull.pref.hypnosis";
export const VOICE_KEY = "lull.pref.voice"; // selected voice persona id (US-005)

// Reads the saved hypnosis-vs-meditation preference, or null if none is stored yet. Error-safe:
// a missing, unreadable, or corrupt value returns null so the caller keeps its own default. The
// default lives at the call site (the toggle's initial state), not duplicated here.
export async function loadHypnosis(): Promise<boolean | null> {
  try {
    const raw = await AsyncStorage.getItem(HYPNOSIS_KEY);
    if (raw === null) return null;
    const parsed = JSON.parse(raw);
    return typeof parsed === "boolean" ? parsed : null;
  } catch {
    return null;
  }
}

// Persists the preference. Swallows write errors — a failed save just means it isn't pre-filled
// next time, which is recoverable and not worth interrupting the session over.
export async function saveHypnosis(value: boolean): Promise<void> {
  try {
    await AsyncStorage.setItem(HYPNOSIS_KEY, JSON.stringify(value));
  } catch {
    // ponytail: best-effort persistence; the toggle still works in-session if the write fails.
  }
}

// Selected voice persona id (US-005). null if none stored yet; the default lives at the call site
// (DEFAULT_VOICE_ID in the context), not duplicated here. Error-safe like the hypnosis pair.
export async function loadVoice(): Promise<string | null> {
  try {
    const raw = await AsyncStorage.getItem(VOICE_KEY);
    // Drop a stored id that no longer maps to a persona (removed/renamed) so the caller falls back
    // to its default rather than sending an unknown persona that /tts would reject with 422.
    return VOICE_PERSONAS.some((p) => p.id === raw) ? raw : null;
  } catch {
    return null;
  }
}

export async function saveVoice(personaId: string): Promise<void> {
  try {
    await AsyncStorage.setItem(VOICE_KEY, personaId);
  } catch {
    // ponytail: best-effort; the picker still works in-session if the write fails.
  }
}
