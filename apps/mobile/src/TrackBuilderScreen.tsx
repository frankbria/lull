import { ScrollView, StyleSheet, Text } from "react-native";
import { StatusBar } from "expo-status-bar";
import { CATEGORIES } from "./catalog";
import { CategorySection } from "./CategorySection";
import { SummaryCard } from "./SummaryCard";
import { Sprint0Harness } from "./Sprint0Harness";

export function TrackBuilderScreen() {
  return (
    <ScrollView contentContainerStyle={styles.container}>
      <StatusBar style="auto" />
      <Text style={styles.title}>Build your track</Text>
      <Text style={styles.subtitle}>
        Every component starts on AI Choice — override any you like.
      </Text>
      {CATEGORIES.map((c) => (
        <CategorySection key={c.id} category={c} />
      ))}
      <SummaryCard />
      {/* Dev-only: generates from DEFAULT_SPEC (not the selections), kept for the device-testing
          loop. Generating from the assembled spec is #13. __DEV__ keeps it out of real builds. */}
      {__DEV__ && <Sprint0Harness />}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 24, paddingTop: 72, paddingBottom: 48 },
  title: { fontSize: 24, fontWeight: "700" },
  subtitle: { fontSize: 14, color: "#666", marginTop: 4 },
});
