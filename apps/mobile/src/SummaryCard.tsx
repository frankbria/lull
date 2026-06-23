import { StyleSheet, Text, View } from "react-native";
import { AI_CHOICE, CATEGORIES } from "./catalog";
import { useTrackBuilder } from "./TrackBuilderContext";

// The script preview. Every category always has a selection (AI_CHOICE by default), so this
// shows from the start and reveals the AI's actual pick for any category still on AI Choice.
export function SummaryCard() {
  const { selections, aiPicks } = useTrackBuilder();
  return (
    <View style={styles.card} accessibilityLabel="Track summary">
      <Text style={styles.title}>Your track</Text>
      {CATEGORIES.map((c) => {
        const isAi = selections[c.id] === AI_CHOICE;
        const chosenId = isAi ? aiPicks[c.id] : selections[c.id];
        const opt = c.options.find((o) => o.id === chosenId);
        return (
          <Text key={c.id} style={styles.row}>
            {c.label}: {opt?.name}
            {isAi ? " (AI Choice)" : ""}
          </Text>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  card: { marginTop: 28, padding: 16, borderRadius: 12, backgroundColor: "#f5f5f5", gap: 4 },
  title: { fontSize: 16, fontWeight: "700", marginBottom: 4 },
  row: { fontSize: 14 },
});
