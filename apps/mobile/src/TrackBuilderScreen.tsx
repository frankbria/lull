import { useRef, useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text } from "react-native";
import { StatusBar } from "expo-status-bar";
import { synthesizeAndPlay } from "./audio";
import { CATEGORIES } from "./catalog";
import { CategorySection } from "./CategorySection";
import { HypnosisToggle } from "./HypnosisToggle";
import { ScriptPreview } from "./ScriptPreview";
import { SummaryCard } from "./SummaryCard";
import { Sprint0Harness } from "./Sprint0Harness";

// Two phases on one screen — no router yet (YAGNI). "build" picks the components; "Generate script"
// moves to "preview" (US-004), where the script is read before any audio. Selection state lives in
// TrackBuilderContext above this screen, so switching phases preserves the chosen components.
export function TrackBuilderScreen() {
  const [phase, setPhase] = useState<"build" | "preview">("build");
  // Audio cleanup (player release / Blob URL revoke) from a "Continue to audio" handoff.
  const audioCleanup = useRef<(() => void) | null>(null);

  async function proceedToAudio(scriptText: string) {
    audioCleanup.current?.();
    audioCleanup.current = await synthesizeAndPlay(scriptText);
  }

  if (phase === "preview") {
    return (
      <ScrollView contentContainerStyle={styles.container}>
        <StatusBar style="auto" />
        <ScriptPreview onBack={() => setPhase("build")} onProceed={proceedToAudio} />
      </ScrollView>
    );
  }

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <StatusBar style="auto" />
      <Text style={styles.title}>Build your track</Text>
      <Text style={styles.subtitle}>
        Every component starts on AI Choice — override any you like.
      </Text>
      <HypnosisToggle />
      {CATEGORIES.map((c) => (
        <CategorySection key={c.id} category={c} />
      ))}
      <SummaryCard />
      <Pressable
        testID="generate-script"
        accessibilityRole="button"
        style={styles.generate}
        onPress={() => setPhase("preview")}
      >
        <Text style={styles.generateText}>Generate script</Text>
      </Pressable>
      {/* Dev-only quick audio check from DEFAULT_SPEC; __DEV__ keeps it out of real builds. */}
      {__DEV__ && <Sprint0Harness />}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 24, paddingTop: 72, paddingBottom: 48 },
  title: { fontSize: 24, fontWeight: "700" },
  subtitle: { fontSize: 14, color: "#666", marginTop: 4 },
  generate: { marginTop: 28, borderRadius: 12, padding: 16, backgroundColor: "#4338ca", alignItems: "center" },
  generateText: { fontSize: 17, fontWeight: "700", color: "#fff" },
});
