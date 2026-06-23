import { useState } from "react";
import { Pressable, Text, View } from "react-native";
import { fireEvent, render, screen } from "@testing-library/react-native";
import { AI_CHOICE, CATEGORIES, type Category } from "../catalog";
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

// Deterministic AI picker for stable assertions: always the second option (index 1), so it is
// distinguishable from the first option used elsewhere in these tests.
const pickSecond = (c: Category) => c.options[1].id;

function aiName(c: Category) {
  return c.options[1].name;
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
  it("renders every category with an AI Choice option plus all concrete options", () => {
    render(
      <TrackBuilderProvider>
        <Builder />
      </TrackBuilderProvider>,
    );
    for (const c of CATEGORIES) {
      expect(screen.getByText(c.label)).toBeTruthy();
      expect(screen.getByTestId(`option-${c.id}-${AI_CHOICE}`)).toBeTruthy();
      for (const o of c.options) {
        expect(screen.getByTestId(`option-${c.id}-${o.id}`)).toBeTruthy();
      }
    }
  });

  it("defaults every category to AI Choice for a first-time user", () => {
    render(
      <TrackBuilderProvider>
        <Builder />
      </TrackBuilderProvider>,
    );
    for (const c of CATEGORIES) {
      const ai = screen.getByTestId(`option-${c.id}-${AI_CHOICE}`);
      expect(ai.props.accessibilityState.selected).toBe(true);
      // No concrete option is selected while AI Choice is active.
      for (const o of c.options) {
        expect(screen.getByTestId(`option-${c.id}-${o.id}`).props.accessibilityState.selected).toBe(
          false,
        );
      }
    }
  });

  it("allows exactly one selection per category (picking a second replaces the first)", () => {
    render(
      <TrackBuilderProvider>
        <Builder />
      </TrackBuilderProvider>,
    );
    const ai = screen.getByTestId(`option-induction-${AI_CHOICE}`);
    const first = screen.getByTestId("option-induction-progressive_relaxation");
    const second = screen.getByTestId("option-induction-fixation");

    fireEvent.press(first);
    expect(ai.props.accessibilityState.selected).toBe(false);
    expect(first.props.accessibilityState.selected).toBe(true);

    fireEvent.press(second);
    expect(first.props.accessibilityState.selected).toBe(false);
    expect(second.props.accessibilityState.selected).toBe(true);
  });

  it("can revert a manual pick back to AI Choice", () => {
    render(
      <TrackBuilderProvider>
        <Builder />
      </TrackBuilderProvider>,
    );
    const ai = screen.getByTestId(`option-induction-${AI_CHOICE}`);
    const first = screen.getByTestId("option-induction-progressive_relaxation");

    fireEvent.press(first);
    expect(first.props.accessibilityState.selected).toBe(true);

    fireEvent.press(ai);
    expect(ai.props.accessibilityState.selected).toBe(true);
    expect(first.props.accessibilityState.selected).toBe(false);
  });

  it("shows the preview immediately, revealing the AI's actual pick for each category", () => {
    render(
      <TrackBuilderProvider aiPicker={pickSecond}>
        <Builder />
      </TrackBuilderProvider>,
    );
    expect(screen.getByText("Your track")).toBeTruthy();
    for (const c of CATEGORIES) {
      // The revealed pick is the AI's concrete choice, marked as an AI Choice.
      expect(screen.getByText(`${c.label}: ${aiName(c)} (AI Choice)`)).toBeTruthy();
    }
  });

  it("reveals a manual pick without the AI marker, and overriding one category leaves the others on AI", () => {
    render(
      <TrackBuilderProvider aiPicker={pickSecond}>
        <Builder />
      </TrackBuilderProvider>,
    );
    fireEvent.press(screen.getByTestId("option-induction-progressive_relaxation"));

    // The overridden category shows the manual pick, no AI marker.
    expect(screen.getByText("Induction: Progressive relaxation")).toBeTruthy();
    expect(screen.queryByText("Induction: Progressive relaxation (AI Choice)")).toBeNull();

    // Every other category is undisturbed — still revealing its AI pick.
    for (const c of CATEGORIES.filter((c) => c.id !== "induction")) {
      expect(screen.getByText(`${c.label}: ${aiName(c)} (AI Choice)`)).toBeTruthy();
    }
  });

  it("keeps a stable AI pick across a preview re-render", () => {
    render(
      <TrackBuilderProvider aiPicker={pickSecond}>
        <Builder />
      </TrackBuilderProvider>,
    );
    // Toggling an unrelated category must not change another category's revealed AI pick.
    expect(screen.getByText(`Body: ${aiName(CATEGORIES[2])} (AI Choice)`)).toBeTruthy();
    fireEvent.press(screen.getByTestId("option-induction-progressive_relaxation"));
    expect(screen.getByText(`Body: ${aiName(CATEGORIES[2])} (AI Choice)`)).toBeTruthy();
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
