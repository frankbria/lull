import { useEffect, useRef } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { VOICE_PERSONAS } from "@lull/shared";
import { playVoicePreview } from "./audio";
import { useTrackBuilder } from "./TrackBuilderContext";

// Voice persona picker (US-005/FR-V1): a radio list of named personas with a one-line descriptor,
// each with a short preview clip (FR-V2). The selected persona is persisted via the context and
// passed to /tts so audio renders in that voice. Raw ElevenLabs ids never reach here — personas
// are the abstraction (packages/shared VOICE_PERSONAS).
export function VoicePicker() {
  const { voiceId, setVoiceId } = useTrackBuilder();
  // One preview plays at a time; release the prior player before the next, and on unmount.
  const previewCleanup = useRef<(() => void) | null>(null);
  const previewBusy = useRef(false);
  const mounted = useRef(true);
  useEffect(() => {
    return () => {
      mounted.current = false;
      previewCleanup.current?.();
    };
  }, []);

  async function preview(personaId: string) {
    if (previewBusy.current) return; // serialize taps so one can't orphan another's player
    previewBusy.current = true;
    try {
      previewCleanup.current?.();
      previewCleanup.current = null;
      const cleanup = await playVoicePreview(personaId);
      // Unmounted while the request was in flight → release now; the unmount effect already ran.
      if (!mounted.current) {
        cleanup();
        return;
      }
      previewCleanup.current = cleanup;
    } finally {
      previewBusy.current = false;
    }
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Voice</Text>
      {VOICE_PERSONAS.map((p) => {
        const active = voiceId === p.id;
        return (
          <Pressable
            key={p.id}
            testID={`voice-${p.id}`}
            accessibilityRole="radio"
            accessibilityState={{ selected: active }}
            onPress={() => setVoiceId(p.id)}
            style={[styles.option, active && styles.optionActive]}
          >
            <View style={styles.text}>
              <Text style={[styles.name, active && styles.nameActive]}>{p.name}</Text>
              <Text testID={`descriptor-${p.id}`} style={styles.descriptor}>
                {p.descriptor}
              </Text>
            </View>
            <Pressable
              testID={`preview-${p.id}`}
              accessibilityRole="button"
              accessibilityLabel={`Preview ${p.name}`}
              hitSlop={8}
              onPress={() => void preview(p.id)}
              style={styles.previewBtn}
            >
              <Text style={styles.previewText}>Preview</Text>
            </Pressable>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { marginTop: 24, gap: 8 },
  title: { fontSize: 18, fontWeight: "600" },
  option: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    borderWidth: 2,
    borderColor: "#ddd",
    borderRadius: 12,
    padding: 14,
  },
  optionActive: { borderColor: "#4338ca", backgroundColor: "#eef2ff" },
  text: { flex: 1, gap: 4 },
  name: { fontSize: 16, fontWeight: "600", color: "#333" },
  nameActive: { color: "#4338ca" },
  descriptor: { fontSize: 13, color: "#666" },
  previewBtn: { borderWidth: 1, borderColor: "#c7d2fe", borderRadius: 8, paddingVertical: 8, paddingHorizontal: 12 },
  previewText: { fontSize: 14, fontWeight: "600", color: "#4338ca" },
});
