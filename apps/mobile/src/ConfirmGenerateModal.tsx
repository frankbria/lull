import { useState } from "react";
import { ActivityIndicator, Modal, Pressable, StyleSheet, Text, View } from "react-native";
import { type ScriptResponse } from "@lull/shared";
import { formatDuration } from "./ScriptPreview";

// US-006: before any audio is generated the user sees the cost/time estimate and must explicitly
// tap "Confirm and Generate". The modal owns the generation lifecycle so it can show the
// script → voice → finalize progress and offer a retry if synthesis fails.
type Stage = "script" | "voice" | "finalize";
const STAGES: { key: Stage; label: string }[] = [
  { key: "script", label: "Preparing script" },
  { key: "voice", label: "Generating voice" },
  { key: "finalize", label: "Finalizing audio" },
];

// Rough client-side estimate of how long synthesis takes — the server doesn't return one. ElevenLabs
// streams near real time plus a fixed handshake; this is deliberately approximate.
// ponytail: flat 15ms/char + 2s heuristic. Tune (or replace with a measured server value) once real
// /tts latencies are known.
export function estimateGenerationSeconds(charCount: number): number {
  return Math.max(3, Math.round(charCount * 0.015 + 2));
}

interface Props {
  report: ScriptResponse;
  onClose: () => void;
  onGenerate: (onProgress: (stage: Stage) => void) => Promise<void>;
}

export function ConfirmGenerateModal({ report, onClose, onGenerate }: Props) {
  const [status, setStatus] = useState<"idle" | "generating" | "error">("idle");
  const [stage, setStage] = useState<Stage | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Duplicate submits are prevented synchronously: the confirm/retry button is removed below while
  // status === "generating", so onGenerate can't be re-entered for a second in-flight request.
  const run = async () => {
    setStatus("generating");
    setStage(null);
    setError(null);
    try {
      await onGenerate(setStage);
      onClose(); // audio is now playing — return to the preview
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setStatus("error");
    }
  };

  return (
    <Modal
      visible
      transparent
      animationType="fade"
      testID="confirm-modal"
      // Android hardware back: ignore mid-generation, else the error/retry surface vanishes off-screen.
      onRequestClose={() => {
        if (status !== "generating") onClose();
      }}
    >
      <View style={styles.backdrop}>
        <View style={styles.card}>
          <Text style={styles.title}>Ready to generate?</Text>

          <View style={styles.estimates}>
            <Text testID="est-chars" style={styles.row}>
              ~{report.char_count.toLocaleString()} characters
            </Text>
            <Text testID="est-length" style={styles.row}>
              ~{formatDuration(report.est_seconds)} of audio
            </Text>
            <Text testID="est-gen-time" style={styles.row}>
              ~{formatDuration(estimateGenerationSeconds(report.char_count))} to generate
            </Text>
            <Text testID="est-cost" style={styles.row}>
              ~${report.est_cost_usd.toFixed(2)} estimated cost
            </Text>
          </View>

          {status === "generating" && (
            <View testID="progress" style={styles.progress}>
              {STAGES.map((s) => {
                const active = stage === s.key;
                return (
                  <Text
                    key={s.key}
                    testID={`stage-${s.key}`}
                    accessibilityState={{ selected: active }}
                    style={[styles.stage, active && styles.stageActive]}
                  >
                    {active ? "● " : "○ "}
                    {s.label}
                  </Text>
                );
              })}
              <ActivityIndicator style={styles.spinner} />
            </View>
          )}

          {status === "error" && (
            <Text testID="generate-error" style={styles.error}>
              {error}
            </Text>
          )}

          <View style={styles.actions}>
            {status !== "generating" && (
              <Pressable
                testID="cancel-generate"
                accessibilityRole="button"
                onPress={onClose}
                style={[styles.button, styles.secondary]}
              >
                <Text style={styles.secondaryText}>Cancel</Text>
              </Pressable>
            )}
            {status === "error" ? (
              <Pressable
                testID="retry-generate"
                accessibilityRole="button"
                onPress={() => void run()}
                style={[styles.button, styles.primary]}
              >
                <Text style={styles.primaryText}>Retry</Text>
              </Pressable>
            ) : status === "idle" ? (
              <Pressable
                testID="confirm-generate"
                accessibilityRole="button"
                onPress={() => void run()}
                style={[styles.button, styles.primary]}
              >
                <Text style={styles.primaryText}>Confirm and Generate</Text>
              </Pressable>
            ) : null}
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: { flex: 1, backgroundColor: "rgba(0,0,0,0.4)", justifyContent: "center", padding: 24 },
  card: { backgroundColor: "#fff", borderRadius: 16, padding: 24, gap: 16 },
  title: { fontSize: 20, fontWeight: "700" },
  estimates: { gap: 6 },
  row: { fontSize: 16, color: "#333" },
  progress: { gap: 8 },
  stage: { fontSize: 15, color: "#999" },
  stageActive: { color: "#4338ca", fontWeight: "700" },
  spinner: { marginTop: 4 },
  error: { color: "#b00" },
  actions: { flexDirection: "row", gap: 12 },
  button: { flex: 1, borderRadius: 12, padding: 14, alignItems: "center" },
  secondary: { borderWidth: 1, borderColor: "#ddd" },
  secondaryText: { fontSize: 16, fontWeight: "600", color: "#333" },
  primary: { backgroundColor: "#4338ca" },
  primaryText: { fontSize: 16, fontWeight: "700", color: "#fff" },
});
