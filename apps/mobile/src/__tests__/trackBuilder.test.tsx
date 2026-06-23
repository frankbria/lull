import { useState } from "react";
import { Pressable, Text, View } from "react-native";
import { fireEvent, render, screen } from "@testing-library/react-native";
import { CATEGORIES } from "../catalog";
import { CategorySection } from "../CategorySection";
import { SummaryCard } from "../SummaryCard";
import { TrackBuilderProvider, useTrackBuilder } from "../TrackBuilderContext";

// Mirrors TrackBuilderScreen's builder portion without the audio harness (keeps expo-audio out of
// the unit tests). Optional `remountKey` forces the sections to unmount/remount while the provider
// (and its selection state) stays mounted — the basis of the persistence test.
function Builder({ remountKey = 0 }: { remountKey?: number }) {
  return (
    <View key={remountKey}>
      {CATEGORIES.map((c) => (
        <CategorySection key={c.id} category={c} />
      ))}
      <SummaryCard />
    </View>
  );
}

function selectFirstOfEach() {
  for (const c of CATEGORIES) {
    fireEvent.press(screen.getByTestId(`option-${c.id}-${c.options[0].id}`));
  }
}

describe("track builder catalog", () => {
  it("offers all four categories", () => {
    expect(CATEGORIES.map((c) => c.id)).toEqual(["induction", "deepener", "body", "ending"]);
  });

  it("offers at least 5 named options with a description per category", () => {
    for (const c of CATEGORIES) {
      expect(c.options.length).toBeGreaterThanOrEqual(5);
      for (const o of c.options) {
        expect(o.name.length).toBeGreaterThan(0);
        expect(o.blurb.length).toBeGreaterThan(0);
      }
    }
  });
});

describe("useTrackBuilder", () => {
  it("throws when used outside a provider", () => {
    function Orphan() {
      useTrackBuilder();
      return null;
    }
    // Silence React's error-boundary console noise for this expected throw.
    const spy = jest.spyOn(console, "error").mockImplementation(() => {});
    expect(() => render(<Orphan />)).toThrow(/TrackBuilderProvider/);
    spy.mockRestore();
  });
});

describe("TrackBuilder UI", () => {
  it("renders every category with its options", () => {
    render(
      <TrackBuilderProvider>
        <Builder />
      </TrackBuilderProvider>,
    );
    for (const c of CATEGORIES) {
      expect(screen.getByText(c.label)).toBeTruthy();
      for (const o of c.options) {
        expect(screen.getByTestId(`option-${c.id}-${o.id}`)).toBeTruthy();
      }
    }
  });

  it("allows exactly one selection per category (picking a second replaces the first)", () => {
    render(
      <TrackBuilderProvider>
        <Builder />
      </TrackBuilderProvider>,
    );
    const first = screen.getByTestId("option-induction-progressive_relaxation");
    const second = screen.getByTestId("option-induction-fixation");

    fireEvent.press(first);
    expect(first.props.accessibilityState.selected).toBe(true);

    fireEvent.press(second);
    expect(first.props.accessibilityState.selected).toBe(false);
    expect(second.props.accessibilityState.selected).toBe(true);
  });

  it("hides the summary until all four are chosen, then shows all four", () => {
    render(
      <TrackBuilderProvider>
        <Builder />
      </TrackBuilderProvider>,
    );
    expect(screen.queryByText("Your track")).toBeNull();

    selectFirstOfEach();

    expect(screen.getByText("Your track")).toBeTruthy();
    for (const c of CATEGORIES) {
      expect(screen.getByText(`${c.label}: ${c.options[0].name}`)).toBeTruthy();
    }
  });

  it("persists selections when the builder subtree remounts", () => {
    // A remount button changes the key on <Builder>, unmounting/remounting the sections while the
    // provider above stays mounted — selections must survive (the "persists across navigation" AC).
    function Wrapper() {
      const [k, setK] = useState(0);
      return (
        <TrackBuilderProvider>
          <Pressable testID="remount" onPress={() => setK((n) => n + 1)}>
            <Text>remount</Text>
          </Pressable>
          <Builder remountKey={k} />
        </TrackBuilderProvider>
      );
    }
    render(<Wrapper />);

    fireEvent.press(screen.getByTestId("option-deepener-staircase"));
    expect(screen.getByTestId("option-deepener-staircase").props.accessibilityState.selected).toBe(
      true,
    );

    fireEvent.press(screen.getByTestId("remount"));

    expect(screen.getByTestId("option-deepener-staircase").props.accessibilityState.selected).toBe(
      true,
    );
  });
});
