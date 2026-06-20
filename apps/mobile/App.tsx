import { useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Button,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { createAudioPlayer } from "expo-audio";
import * as FileSystem from "expo-file-system";
import { StatusBar } from "expo-status-bar";
import { DEFAULT_SPEC, type ScriptResponse } from "@lull/shared";

// Sprint-0 test harness: build a script, preview it, render to audio, and play it.
// Device note: localhost won't reach your dev machine. Use the Android emulator host
// (10.0.2.2), or your machine's LAN IP, via EXPO_PUBLIC_API_BASE.
const API_BASE = process.env.EXPO_PUBLIC_API_BASE ?? "http://localhost:8000";

export default function App() {
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<ScriptResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // expo-audio's imperative players don't auto-release; track + clean up to avoid leaks.
  const playerRef = useRef<ReturnType<typeof createAudioPlayer> | null>(null);
  const webUrlRef = useRef<string | null>(null);

  function cleanupPlayback() {
    playerRef.current?.remove();
    playerRef.current = null;
    if (webUrlRef.current) {
      URL.revokeObjectURL(webUrlRef.current);
      webUrlRef.current = null;
    }
  }

  useEffect(() => cleanupPlayback, []);

  async function generateAndPlay() {
    setBusy(true);
    setError(null);
    cleanupPlayback(); // release any prior player/Blob URL before a new run
    try {
      const sres = await fetch(`${API_BASE}/script`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(DEFAULT_SPEC),
      });
      if (!sres.ok) throw new Error(`/script ${sres.status}`);
      const script: ScriptResponse = await sres.json();
      setResult(script);

      const tres = await fetch(`${API_BASE}/tts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: script.script }),
      });
      if (!tres.ok) throw new Error(`/tts ${tres.status}`);
      const bytes = new Uint8Array(await tres.arrayBuffer());

      const uri = await audioUri(bytes);
      if (Platform.OS === "web") webUrlRef.current = uri; // revoked on next run / unmount
      // ponytail: web browsers may block play() here since the awaited fetches consume the
      // click's user-activation — device playback is the real target (#24).
      playerRef.current = createAudioPlayer(uri);
      playerRef.current.play();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <StatusBar style="auto" />
      <Text style={styles.title}>Lull — Sprint 0 harness</Text>
      <Button title="Generate & play" onPress={generateAndPlay} disabled={busy} />
      {busy && <ActivityIndicator style={styles.spacer} />}
      {error && <Text style={styles.error}>{error}</Text>}
      {result && (
        <View style={styles.spacer}>
          <Text style={styles.meta}>
            {result.char_count} chars · ~{Math.round(result.est_seconds)}s · ~$
            {result.est_cost_usd} · {JSON.stringify(result.components)}
          </Text>
          <Text style={styles.script}>{result.script}</Text>
        </View>
      )}
    </ScrollView>
  );
}

// Web (expo-file-system is native-only): play straight from a Blob URL.
// Native: write the bytes to the cache as base64 and play the file.
async function audioUri(bytes: Uint8Array): Promise<string> {
  if (Platform.OS === "web") {
    const blob = new Blob([bytes], { type: "audio/wav" });
    return URL.createObjectURL(blob);
  }
  const uri = `${FileSystem.cacheDirectory}lull-session.wav`;
  await FileSystem.writeAsStringAsync(uri, base64FromBytes(bytes), {
    encoding: FileSystem.EncodingType.Base64,
  });
  return uri;
}

const B64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

function base64FromBytes(bytes: Uint8Array): string {
  let out = "";
  for (let i = 0; i < bytes.length; i += 3) {
    const b0 = bytes[i];
    const b1 = bytes[i + 1] ?? 0;
    const b2 = bytes[i + 2] ?? 0;
    out += B64[b0 >> 2];
    out += B64[((b0 & 3) << 4) | (b1 >> 4)];
    out += i + 1 < bytes.length ? B64[((b1 & 15) << 2) | (b2 >> 6)] : "=";
    out += i + 2 < bytes.length ? B64[b2 & 63] : "=";
  }
  return out;
}

const styles = StyleSheet.create({
  container: { padding: 24, paddingTop: 72, gap: 12 },
  title: { fontSize: 20, fontWeight: "600" },
  spacer: { marginTop: 16 },
  meta: { fontSize: 12, color: "#666", marginBottom: 8 },
  script: { fontSize: 16, lineHeight: 24 },
  error: { color: "#b00", marginTop: 16 },
});
