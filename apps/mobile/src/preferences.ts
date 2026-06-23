import AsyncStorage from "@react-native-async-storage/async-storage";

// Persisted user preferences. One key for now (US-003); add more here as they appear.
export const HYPNOSIS_KEY = "lull.pref.hypnosis";

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
