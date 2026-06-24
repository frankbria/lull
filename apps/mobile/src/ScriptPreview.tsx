import { useCallback, useEffect, useRef, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { DEFAULT_SPEC, type ScriptResponse } from "@lull/shared";
import { apiBase } from "./apiBase";
import { useTrackBuilder } from "./TrackBuilderContext";

// US-004: read the script before any audio is produced. Generating returns the script *text* first
// (never audio); "Continue to audio" stays locked until the user has scrolled through ≥50% of it.
// ponytail: generation uses DEFAULT_SPEC + the hypnosis toggle — the spec the API fully supports
// today. Wiring the builder's per-component picks into the spec is #13 (Confirm & Generate).
interface Props {
  onBack: () => void;
  onProceed: (scriptText: string) => void | Promise<void>;
}

export function ScriptPreview({ onBack, onProceed }: Props) {
  const { hypnosis } = useTrackBuilder();
  const [result, setResult] = useState<ScriptResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // The scroll gate: false until the user has read ≥50% of the script. Reset on every (re)generate.
  const [unlocked, setUnlocked] = useState(false);
  // Bumped per generation; keys the ScrollView so a regenerated script remounts and fires fresh
  // layout/content-size callbacks — otherwise a short script with an unchanged height could leave
  // the gate stuck (no scroll range, no measure callback). Also resets scroll to the top.
  const [generation, setGeneration] = useState(0);

  // Latest measured viewport/content heights, so a short script that fits without scrolling can
  // unlock on layout (the user can already see ≥50%) rather than trapping them.
  const viewportH = useRef(0);
  const contentH = useRef(0);
  const evaluate = useCallback((offsetY: number, vH: number, cH: number) => {
    if (cH <= 0 || vH <= 0) return;
    const scrollable = cH - vH;
    // Fits entirely → already fully visible, don't trap the user. Otherwise the AC is literal:
    // the gate opens once they've scrolled ≥50% of the way down the script.
    if (scrollable <= 0 || offsetY / scrollable >= 0.5) setUnlocked(true);
  }, []);

  const generate = useCallback(async () => {
    setBusy(true);
    setError(null);
    setUnlocked(false); // a fresh script must be re-read before proceeding to audio
    contentH.current = 0; // force the next measure callback to re-decide the gate
    try {
      const res = await fetch(`${apiBase()}/script`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...DEFAULT_SPEC, hypnosis }),
      });
      if (!res.ok) throw new Error(`/script ${res.status}`);
      setResult((await res.json()) as ScriptResponse);
      setGeneration((g) => g + 1);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }, [hypnosis]);

  // Arriving at the preview *is* "Generate" — produce the script text on entry. Fetch-on-mount is
  // the documented exception to set-state-in-effect (the loading flag must flip before the await).
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void generate();
  }, [generate]);

  return (
    <View style={styles.container}>
      <Pressable testID="back-to-track" accessibilityRole="button" onPress={onBack} hitSlop={8}>
        <Text style={styles.back}>← Back to track</Text>
      </Pressable>
      <Text style={styles.title}>Your script</Text>

      {busy && !result && <ActivityIndicator style={styles.spacer} />}
      {error && (
        <Text testID="preview-error" style={styles.error}>
          {error}
        </Text>
      )}

      {result && (
        <>
          <Text testID="est-duration" style={styles.meta}>
            Estimated length: {formatDuration(result.est_seconds)}
          </Text>
          <ScrollView
            key={generation}
            testID="script-scroll"
            style={styles.scroll}
            // The screen wraps this in an outer ScrollView; Android needs this for the inner one to
            // scroll independently (and fire onScroll), otherwise the 50% gate can never unlock.
            nestedScrollEnabled
            scrollEventThrottle={16}
            onLayout={(e) => {
              viewportH.current = e.nativeEvent.layout.height;
              evaluate(0, viewportH.current, contentH.current);
            }}
            onContentSizeChange={(_w, h) => {
              contentH.current = h;
              evaluate(0, viewportH.current, h);
            }}
            onScroll={(e) => {
              const { contentOffset, layoutMeasurement, contentSize } = e.nativeEvent;
              viewportH.current = layoutMeasurement.height;
              contentH.current = contentSize.height;
              evaluate(contentOffset.y, layoutMeasurement.height, contentSize.height);
            }}
          >
            <Text testID="script-text" style={styles.script}>
              {result.script}
            </Text>
          </ScrollView>

          {!unlocked && <Text style={styles.hint}>Scroll through at least half the script to continue.</Text>}

          <View style={styles.actions}>
            <Pressable
              testID="regenerate"
              accessibilityRole="button"
              onPress={() => void generate()}
              disabled={busy}
              style={[styles.button, styles.secondary, busy && styles.buttonDisabled]}
            >
              <Text style={styles.secondaryText}>Regenerate</Text>
            </Pressable>
            <Pressable
              testID="continue-audio"
              accessibilityRole="button"
              accessibilityState={{ disabled: !unlocked }}
              disabled={!unlocked}
              // onProceed (audio synthesis + playback) can reject on network/audio failure; surface
              // it like the generate path instead of leaking an unhandled rejection.
              onPress={() => {
                setError(null);
                Promise.resolve(onProceed(result.script)).catch((e) =>
                  setError(e instanceof Error ? e.message : String(e)),
                );
              }}
              style={[styles.button, styles.primary, !unlocked && styles.buttonDisabled]}
            >
              <Text style={styles.primaryText}>Continue to audio</Text>
            </Pressable>
          </View>
        </>
      )}
    </View>
  );
}

// Whole seconds into a friendly length: "45 sec" under a minute, "m:ss" above.
export function formatDuration(seconds: number): string {
  const total = Math.round(seconds);
  if (total < 60) return `${total} sec`;
  const mins = Math.floor(total / 60);
  const secs = total % 60;
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

const styles = StyleSheet.create({
  container: { gap: 12 },
  back: { fontSize: 15, color: "#4338ca" },
  title: { fontSize: 24, fontWeight: "700" },
  meta: { fontSize: 14, color: "#666" },
  scroll: { maxHeight: 360, borderWidth: 1, borderColor: "#eee", borderRadius: 12, padding: 16 },
  script: { fontSize: 18, lineHeight: 28, color: "#222" }, // ≥16pt, readable (AC)
  hint: { fontSize: 13, color: "#999", fontStyle: "italic" },
  spacer: { marginTop: 16 },
  error: { color: "#b00", marginTop: 8 },
  actions: { flexDirection: "row", gap: 12, marginTop: 4 },
  button: { flex: 1, borderRadius: 12, padding: 14, alignItems: "center" },
  secondary: { borderWidth: 1, borderColor: "#ddd" },
  secondaryText: { fontSize: 16, fontWeight: "600", color: "#333" },
  primary: { backgroundColor: "#4338ca" },
  primaryText: { fontSize: 16, fontWeight: "700", color: "#fff" },
  buttonDisabled: { opacity: 0.4 },
});
