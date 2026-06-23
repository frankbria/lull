import { StyleSheet, Text, View } from "react-native";
import { CATEGORIES } from "./catalog";
import { useTrackBuilder } from "./TrackBuilderContext";

// Shows the four chosen components once every category has a selection ("before proceeding").
export function SummaryCard() {
  const { selections } = useTrackBuilder();
  const allChosen = CATEGORIES.every((c) => selections[c.id]);
  if (!allChosen) return null;
  return (
    <View style={styles.card} accessibilityLabel="Track summary">
      <Text style={styles.title}>Your track</Text>
      {CATEGORIES.map((c) => {
        const opt = c.options.find((o) => o.id === selections[c.id]);
        return (
          <Text key={c.id} style={styles.row}>
            {c.label}: {opt?.name}
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
