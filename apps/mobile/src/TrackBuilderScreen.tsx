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
      <Text style={styles.subtitle}>Pick one option in each category.</Text>
      {CATEGORIES.map((c) => (
        <CategorySection key={c.id} category={c} />
      ))}
      <SummaryCard />
      <Sprint0Harness />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 24, paddingTop: 72, paddingBottom: 48 },
  title: { fontSize: 24, fontWeight: "700" },
  subtitle: { fontSize: 14, color: "#666", marginTop: 4 },
});
