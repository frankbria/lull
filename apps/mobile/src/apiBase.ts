import Constants from "expo-constants";

// API base resolution (dev): the API runs on the SAME host as the Metro bundler this app connected
// to — derive it from Expo's hostUri (e.g. "100.66.225.26:8081" -> :8000) so a real device just
// works over LAN/Tailscale with no per-machine IP to set. Explicit EXPO_PUBLIC_API_BASE wins
// (staging/prod); localhost is the last resort (web / simulator / node tests).
function devApiBase(): string | undefined {
  const host = Constants.expoConfig?.hostUri?.split(":")[0]; // strip the Metro port
  return host ? `http://${host}:8000` : undefined;
}

export function apiBase(): string {
  return process.env.EXPO_PUBLIC_API_BASE ?? devApiBase() ?? "http://localhost:8000";
}
