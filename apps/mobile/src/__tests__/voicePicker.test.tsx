import AsyncStorage from "@react-native-async-storage/async-storage";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react-native";
import { DEFAULT_VOICE_ID, VOICE_PERSONAS } from "@lull/shared";
import { TrackBuilderProvider } from "../TrackBuilderContext";
import { VoicePicker } from "../VoicePicker";
import { TrackBuilderScreen } from "../TrackBuilderScreen";
import { loadVoice, saveVoice, VOICE_KEY } from "../preferences";
import { playVoicePreview, synthesizeAndPlay } from "../audio";

// Audio is network + native players; stub it so the picker/screen logic is what's under test.
jest.mock("../audio", () => ({
  playVoicePreview: jest.fn(),
  synthesizeAndPlay: jest.fn(),
}));

const previewMock = playVoicePreview as jest.Mock;
const synthMock = synthesizeAndPlay as jest.Mock;

beforeEach(async () => {
  await AsyncStorage.clear();
  previewMock.mockReset().mockResolvedValue(() => {});
  synthMock.mockReset().mockResolvedValue(() => {});
});

function renderPicker() {
  render(
    <TrackBuilderProvider>
      <VoicePicker />
    </TrackBuilderProvider>,
  );
}

describe("preferences (voice persistence)", () => {
  it("returns null when nothing is stored (caller keeps its default)", async () => {
    await expect(loadVoice()).resolves.toBeNull();
  });

  it("round-trips the saved persona id", async () => {
    await saveVoice("james");
    await expect(loadVoice()).resolves.toBe("james");
  });

  it("drops a stored id that no longer maps to a persona (falls back to the default)", async () => {
    await AsyncStorage.setItem(VOICE_KEY, "retired-voice");
    await expect(loadVoice()).resolves.toBeNull();
  });
});

describe("VoicePicker (US-005)", () => {
  it("renders at least six personas, each with a name and a descriptor (AC1)", () => {
    expect(VOICE_PERSONAS.length).toBeGreaterThanOrEqual(6);
    renderPicker();
    for (const p of VOICE_PERSONAS) {
      expect(screen.getByTestId(`voice-${p.id}`)).toBeTruthy();
      expect(screen.getByText(p.name)).toBeTruthy();
      expect(screen.getByTestId(`descriptor-${p.id}`).props.children.length).toBeGreaterThan(0);
    }
  });

  it("selects a default persona for a first-time user", () => {
    renderPicker();
    expect(screen.getByTestId(`voice-${DEFAULT_VOICE_ID}`).props.accessibilityState.selected).toBe(
      true,
    );
  });

  it("changes and persists the selection when a persona is tapped (AC3 'selection saved')", async () => {
    renderPicker();
    fireEvent.press(screen.getByTestId("voice-james"));
    expect(screen.getByTestId("voice-james").props.accessibilityState.selected).toBe(true);
    expect(screen.getByTestId(`voice-${DEFAULT_VOICE_ID}`).props.accessibilityState.selected).toBe(
      false,
    );
    await waitFor(() => expect(loadVoice()).resolves.toBe("james"));
  });

  it("pre-fills the saved persona on the next app launch", async () => {
    await AsyncStorage.setItem(VOICE_KEY, "lily");
    render(
      <TrackBuilderProvider>
        <VoicePicker />
      </TrackBuilderProvider>,
    );
    await waitFor(() =>
      expect(screen.getByTestId("voice-lily").props.accessibilityState.selected).toBe(true),
    );
  });

  it("plays that persona's preview clip when Preview is tapped (AC2)", async () => {
    renderPicker();
    fireEvent.press(screen.getByTestId("preview-sarah"));
    await waitFor(() => expect(previewMock).toHaveBeenCalledWith("sarah"));
  });
});

// AC3: changing the voice after a track has rendered must trigger a re-render. With no persisted
// track, that means the stale audio is released so the next play re-synthesizes in the new voice.
describe("voice change after generation (US-005/FR-V4)", () => {
  const SCRIPT = { script: "Rest now.\n\n".repeat(20).trim(), est_seconds: 130 };
  const originalFetch = global.fetch;
  beforeEach(() => {
    global.fetch = jest
      .fn()
      .mockResolvedValue({ ok: true, json: async () => SCRIPT }) as unknown as typeof fetch;
  });
  afterEach(() => {
    global.fetch = originalFetch;
  });

  it("renders audio in the selected voice, then releases it when the voice changes", async () => {
    const cleanup = jest.fn();
    synthMock.mockResolvedValue(cleanup);
    render(
      <TrackBuilderProvider>
        <TrackBuilderScreen />
      </TrackBuilderProvider>,
    );

    // Build -> preview, read the script, continue to audio.
    fireEvent.press(screen.getByTestId("generate-script"));
    await screen.findByTestId("script-text");
    fireEvent.scroll(screen.getByTestId("script-scroll"), {
      nativeEvent: {
        contentOffset: { y: 100 },
        layoutMeasurement: { height: 100 },
        contentSize: { height: 200 },
      },
    });
    await act(async () => {
      fireEvent.press(screen.getByTestId("continue-audio"));
    });
    expect(synthMock).toHaveBeenCalledWith(SCRIPT.script, DEFAULT_VOICE_ID);

    // Back to build, change the voice -> the rendered audio is released (re-render).
    fireEvent.press(screen.getByTestId("back-to-track"));
    fireEvent.press(screen.getByTestId("voice-james"));
    expect(cleanup).toHaveBeenCalled();
  });

  it("discards a render that finishes after the voice changed mid-synthesis", async () => {
    // Synthesis is in flight when the user changes voice; when it resolves it must NOT start playing
    // in the now-stale voice — the resolved player is released instead.
    const cleanup = jest.fn();
    let resolveSynth: () => void = () => {};
    synthMock.mockReturnValue(
      new Promise<() => void>((res) => {
        resolveSynth = () => res(cleanup);
      }),
    );
    render(
      <TrackBuilderProvider>
        <TrackBuilderScreen />
      </TrackBuilderProvider>,
    );

    fireEvent.press(screen.getByTestId("generate-script"));
    await screen.findByTestId("script-text");
    fireEvent.scroll(screen.getByTestId("script-scroll"), {
      nativeEvent: {
        contentOffset: { y: 100 },
        layoutMeasurement: { height: 100 },
        contentSize: { height: 200 },
      },
    });
    fireEvent.press(screen.getByTestId("continue-audio")); // synth now pending

    // Change voice while the synth is still pending, then let it resolve.
    fireEvent.press(screen.getByTestId("back-to-track"));
    fireEvent.press(screen.getByTestId("voice-james"));
    await act(async () => {
      resolveSynth();
    });
    expect(cleanup).toHaveBeenCalled(); // stale playback released, not kept
  });
});
