import { useState } from "react";
import { Pressable, Text, View } from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react-native";
import { HypnosisToggle } from "../HypnosisToggle";
import { HYPNOSIS_KEY, loadHypnosis, saveHypnosis } from "../preferences";
import { TrackBuilderProvider } from "../TrackBuilderContext";

beforeEach(async () => {
  await AsyncStorage.clear();
});

function Screen({ remountKey = 0 }: { remountKey?: number }) {
  return (
    <View key={remountKey}>
      <HypnosisToggle />
    </View>
  );
}

describe("preferences (hypnosis persistence)", () => {
  it("returns null when nothing is stored (caller keeps its default)", async () => {
    await expect(loadHypnosis()).resolves.toBeNull();
  });

  it("round-trips the saved preference", async () => {
    await saveHypnosis(false);
    await expect(loadHypnosis()).resolves.toBe(false);
    await saveHypnosis(true);
    await expect(loadHypnosis()).resolves.toBe(true);
  });

  it("returns null if the stored value is corrupt", async () => {
    await AsyncStorage.setItem(HYPNOSIS_KEY, "not-json");
    await expect(loadHypnosis()).resolves.toBeNull();
  });
});

describe("HypnosisToggle", () => {
  it("renders both modes, each with a one-sentence explainer", () => {
    render(
      <TrackBuilderProvider>
        <Screen />
      </TrackBuilderProvider>,
    );
    expect(screen.getByTestId("toggle-hypnosis")).toBeTruthy();
    expect(screen.getByTestId("toggle-meditation")).toBeTruthy();
    expect(screen.getByText("True Hypnosis")).toBeTruthy();
    expect(screen.getByText("Plain Meditation")).toBeTruthy();
    // One-sentence explainer under each mode.
    expect(screen.getByTestId("explainer-hypnosis").props.children.length).toBeGreaterThan(0);
    expect(screen.getByTestId("explainer-meditation").props.children.length).toBeGreaterThan(0);
  });

  it("defaults to True Hypnosis for a first-time user", () => {
    render(
      <TrackBuilderProvider>
        <Screen />
      </TrackBuilderProvider>,
    );
    expect(screen.getByTestId("toggle-hypnosis").props.accessibilityState.selected).toBe(true);
    expect(screen.getByTestId("toggle-meditation").props.accessibilityState.selected).toBe(false);
  });

  it("switches to Plain Meditation when tapped", () => {
    render(
      <TrackBuilderProvider>
        <Screen />
      </TrackBuilderProvider>,
    );
    fireEvent.press(screen.getByTestId("toggle-meditation"));
    expect(screen.getByTestId("toggle-meditation").props.accessibilityState.selected).toBe(true);
    expect(screen.getByTestId("toggle-hypnosis").props.accessibilityState.selected).toBe(false);
  });

  it("persists the choice and pre-fills it on the next app launch", async () => {
    // Remounting the *provider* (not just the toggle) discards in-memory state, so the only way
    // Plain Meditation can come back is by being loaded from storage — a real "next launch".
    function Wrapper() {
      const [k, setK] = useState(0);
      return (
        <View>
          <Pressable testID="relaunch" onPress={() => setK((n) => n + 1)}>
            <Text>relaunch</Text>
          </Pressable>
          <TrackBuilderProvider key={k}>
            <Screen />
          </TrackBuilderProvider>
        </View>
      );
    }
    render(<Wrapper />);

    fireEvent.press(screen.getByTestId("toggle-meditation"));
    // The write is async; wait until it lands in storage.
    await waitFor(() => expect(loadHypnosis()).resolves.toBe(false));

    // Fresh provider: it starts on the default, then the loaded preference pre-fills Plain
    // Meditation. The async load resolves inside act() so its state update is flushed cleanly.
    await act(async () => {
      fireEvent.press(screen.getByTestId("relaunch"));
    });
    await waitFor(() =>
      expect(screen.getByTestId("toggle-meditation").props.accessibilityState.selected).toBe(true),
    );
  });

  it("does not clobber a choice the user makes before the saved value loads", async () => {
    // True Hypnosis is stored, but the user taps Plain Meditation before the async load resolves.
    // The load must not overwrite that fresh choice.
    await saveHypnosis(true);
    render(
      <TrackBuilderProvider>
        <Screen />
      </TrackBuilderProvider>,
    );
    // Tap immediately, before loadHypnosis()'s promise resolves.
    fireEvent.press(screen.getByTestId("toggle-meditation"));
    // Flush the pending load; the user's choice must survive it.
    await act(async () => {});
    expect(screen.getByTestId("toggle-meditation").props.accessibilityState.selected).toBe(true);
  });
});
