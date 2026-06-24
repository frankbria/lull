import { useEffect, useRef, useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text } from "react-native";
import { StatusBar } from "expo-status-bar";
import { synthesizeAndPlay } from "./audio";
import { CATEGORIES } from "./catalog";
import { CategorySection } from "./CategorySection";
import { HypnosisToggle } from "./HypnosisToggle";
import { ScriptPreview } from "./ScriptPreview";
import { SummaryCard } from "./SummaryCard";
import { useTrackBuilder } from "./TrackBuilderContext";
import { VoicePicker } from "./VoicePicker";
import { Sprint0Harness } from "./Sprint0Harness";

// Two phases on one screen — no router yet (YAGNI). "build" picks the components; "Generate script"
// moves to "preview" (US-004), where the script is read before any audio. Selection state lives in
// TrackBuilderContext above this screen, so switching phases preserves the chosen components.
export function TrackBuilderScreen() {
  const [phase, setPhase] = useState<"build" | "preview">("build");
  const { voiceId } = useTrackBuilder();
  // Audio cleanup (player release / Blob URL revoke) from a "Continue to audio" handoff.
  const audioCleanup = useRef<(() => void) | null>(null);
  const audioBusy = useRef(false); // serialize handoffs so rapid taps can't orphan a player
  // Bumped whenever the current render is invalidated (voice change / unmount); a synth that finishes
  // under a stale token discards its player instead of playing the wrong voice.
  const playToken = useRef(0);
  // Release the player if the user leaves the screen mid-playback.
  useEffect(() => () => audioCleanup.current?.(), []);

  // US-005/FR-V4: changing the voice after a track has been rendered must trigger a re-render. With
  // no persisted track yet, that means dropping the now-stale audio so the next "Continue to audio"
  // re-synthesizes in the newly chosen voice — and invalidating any synth still in flight under the
  // old voice. (Skips the initial mount/load — cleanup is null then.)
  useEffect(() => {
    playToken.current += 1;
    audioCleanup.current?.();
    audioCleanup.current = null;
  }, [voiceId]);

  async function proceedToAudio(scriptText: string) {
    if (audioBusy.current) return; // a synth/play run is already in flight
    audioBusy.current = true;
    const token = playToken.current;
    try {
      audioCleanup.current?.(); // release any prior player before starting a new one
      audioCleanup.current = null;
      const cleanup = await synthesizeAndPlay(scriptText, voiceId);
      // Voice changed while we were synthesizing → this playback is in the old voice; discard it.
      if (token !== playToken.current) {
        cleanup();
        return;
      }
      audioCleanup.current = cleanup;
    } finally {
      audioBusy.current = false;
    }
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
      <VoicePicker />
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
