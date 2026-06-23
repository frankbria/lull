import { Pressable, StyleSheet, Text, View } from "react-native";
import { useTrackBuilder } from "./TrackBuilderContext";

// Prominent True Hypnosis <-> Plain Meditation toggle (US-003). Two segmented options, each with a
// one-sentence explainer; the active one is highlighted. Drives the persisted `hypnosis` preference.
const MODES = [
  {
    key: "hypnosis",
    value: true,
    label: "True Hypnosis",
    explainer: "Direct suggestions guide you into a deep, focused trance.",
  },
  {
    key: "meditation",
    value: false,
    label: "Plain Meditation",
    explainer: "Gentle, open awareness with no hypnotic suggestion.",
  },
] as const;

export function HypnosisToggle() {
  const { hypnosis, setHypnosis } = useTrackBuilder();
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Session style</Text>
      <View style={styles.row}>
        {MODES.map((m) => {
          const active = hypnosis === m.value;
          return (
            <Pressable
              key={m.key}
              testID={`toggle-${m.key}`}
              accessibilityRole="radio"
              accessibilityState={{ selected: active }}
              onPress={() => setHypnosis(m.value)}
              style={[styles.option, active && styles.optionActive]}
            >
              <Text style={[styles.label, active && styles.labelActive]}>{m.label}</Text>
              <Text testID={`explainer-${m.key}`} style={styles.explainer}>
                {m.explainer}
              </Text>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { marginTop: 8, gap: 8 },
  title: { fontSize: 18, fontWeight: "600" },
  row: { flexDirection: "row", gap: 12 },
  option: {
    flex: 1,
    borderWidth: 2,
    borderColor: "#ddd",
    borderRadius: 12,
    padding: 14,
    gap: 4,
  },
  optionActive: { borderColor: "#4338ca", backgroundColor: "#eef2ff" },
  label: { fontSize: 16, fontWeight: "600", color: "#333" },
  labelActive: { color: "#4338ca" },
  explainer: { fontSize: 13, color: "#666" },
});
