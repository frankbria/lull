import { useState } from "react";
import { ActivityIndicator, Button, ScrollView, StyleSheet, Text, View } from "react-native";
import { Audio } from "expo-av";
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

  async function generateAndPlay() {
    setBusy(true);
    setError(null);
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
      const bytes = await tres.arrayBuffer();
      const b64 = arrayBufferToBase64(bytes);
      const uri = `${FileSystem.cacheDirectory}lull-session.wav`;
      await FileSystem.writeAsStringAsync(uri, b64, { encoding: FileSystem.EncodingType.Base64 });

      const { sound } = await Audio.Sound.createAsync({ uri }, { shouldPlay: true });
      void sound; // playback fires on load
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

function arrayBufferToBase64(buffer: ArrayBuffer): string {
  let binary = "";
  const bytes = new Uint8Array(buffer);
  for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
  return global.btoa(binary);
}

const styles = StyleSheet.create({
  container: { padding: 24, paddingTop: 72, gap: 12 },
  title: { fontSize: 20, fontWeight: "600" },
  spacer: { marginTop: 16 },
  meta: { fontSize: 12, color: "#666", marginBottom: 8 },
  script: { fontSize: 16, lineHeight: 24 },
  error: { color: "#b00", marginTop: 16 },
});
