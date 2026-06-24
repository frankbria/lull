import { useEffect, useRef, useState } from "react";
import { ActivityIndicator, Button, StyleSheet, Text, View } from "react-native";
import { DEFAULT_SPEC, type ScriptResponse } from "@lull/shared";
import { apiBase } from "./apiBase";
import { synthesizeAndPlay } from "./audio";
import { useTrackBuilder } from "./TrackBuilderContext";

// Sprint-0 test harness: build a script, render to audio, and play it in one shot.
// ponytail: still wired to DEFAULT_SPEC so the device-testing loop keeps working. The production
// preview-before-audio flow (script first, scroll gate) is US-004 / ScriptPreview; assembling the
// builder's per-component spec is #13. This harness stays __DEV__-only for quick audio checks.
export function Sprint0Harness() {
  const { hypnosis } = useTrackBuilder();
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<ScriptResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // synthesizeAndPlay returns a cleanup (player release / Blob URL revoke); run it on next run + unmount.
  const cleanupRef = useRef<(() => void) | null>(null);
  function cleanupPlayback() {
    cleanupRef.current?.();
    cleanupRef.current = null;
  }
  useEffect(() => cleanupPlayback, []);

  async function generateAndPlay() {
    setBusy(true);
    setError(null);
    cleanupPlayback(); // release any prior player/Blob URL before a new run
    try {
      // Components still come from DEFAULT_SPEC (assembled-spec generation is #13), but the
      // hypnosis-vs-meditation toggle feeds the prompt now (US-003).
      const sres = await fetch(`${apiBase()}/script`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...DEFAULT_SPEC, hypnosis }),
      });
      if (!sres.ok) throw new Error(`/script ${sres.status}`);
      const script: ScriptResponse = await sres.json();
      setResult(script);
      // ponytail: web browsers may block play() here since the awaited fetches consume the click's
      // user-activation — device playback is the real target (#24).
      cleanupRef.current = await synthesizeAndPlay(script.script);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <View style={styles.harness}>
      <Text style={styles.harnessTitle}>Sprint-0 preview (default track)</Text>
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
    </View>
  );
}

const styles = StyleSheet.create({
  harness: { marginTop: 32, borderTopWidth: 1, borderTopColor: "#eee", paddingTop: 16, gap: 8 },
  harnessTitle: { fontSize: 13, color: "#999", textTransform: "uppercase", letterSpacing: 0.5 },
  spacer: { marginTop: 16 },
  meta: { fontSize: 12, color: "#666", marginBottom: 8 },
  script: { fontSize: 16, lineHeight: 24 },
  error: { color: "#b00", marginTop: 16 },
});
