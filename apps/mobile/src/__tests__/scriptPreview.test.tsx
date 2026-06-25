import { fireEvent, render, screen, waitFor } from "@testing-library/react-native";
import { ScriptPreview } from "../ScriptPreview";
import { TrackBuilderProvider } from "../TrackBuilderContext";

// A script long enough that the AC's "scroll ≥50%" gate is meaningful.
const SCRIPT_RESPONSE = {
  script: "Make yourself comfortable.\n\n".repeat(20).trim(),
  char_count: 600,
  est_seconds: 130, // 2:10
  est_cost_usd: 0.01,
  components: { induction: "progressive_relaxation", deepener: "staircase", body: "calm_presence", ending: "gentle_emergence" },
};

function mockFetch() {
  return jest.fn().mockResolvedValue({ ok: true, json: async () => SCRIPT_RESPONSE });
}

function renderPreview(overrides: { onProceed?: jest.Mock; onBack?: jest.Mock } = {}) {
  const onProceed = overrides.onProceed ?? jest.fn();
  const onBack = overrides.onBack ?? jest.fn();
  render(
    <TrackBuilderProvider>
      <ScriptPreview onProceed={onProceed} onBack={onBack} />
    </TrackBuilderProvider>,
  );
  return { onProceed, onBack };
}

// Drives the scroll gate directly from a real-shaped onScroll event.
function scrollTo(offsetY: number, viewportH: number, contentH: number) {
  fireEvent.scroll(screen.getByTestId("script-scroll"), {
    nativeEvent: {
      contentOffset: { y: offsetY },
      layoutMeasurement: { height: viewportH },
      contentSize: { height: contentH },
    },
  });
}

describe("ScriptPreview (US-004)", () => {
  const originalFetch = global.fetch;
  let fetchMock: jest.Mock;
  beforeEach(() => {
    fetchMock = mockFetch();
    global.fetch = fetchMock as unknown as typeof fetch;
  });
  afterEach(() => {
    global.fetch = originalFetch; // don't leak the mock into other suites
  });

  const scriptCalls = () =>
    fetchMock.mock.calls.filter((c) => String(c[0]).endsWith("/script")).length;

  it("produces script text first, and never requests audio", async () => {
    renderPreview();
    expect(await screen.findByTestId("script-text")).toHaveTextContent(/Make yourself comfortable\./);
    const urls = fetchMock.mock.calls.map((c) => String(c[0]));
    expect(urls.some((u) => u.endsWith("/script"))).toBe(true);
    expect(urls.some((u) => u.includes("/tts"))).toBe(false);
  });

  it("shows the estimated duration", async () => {
    renderPreview();
    expect(await screen.findByTestId("est-duration")).toHaveTextContent(/2:10/);
  });

  it("gates 'Continue to audio' until scrolled ≥50%", async () => {
    const { onProceed } = renderPreview();
    const before = await screen.findByTestId("continue-audio");
    expect(before.props.accessibilityState.disabled).toBe(true);
    fireEvent.press(before);
    expect(onProceed).not.toHaveBeenCalled();

    // Scrollable range = content − viewport = 700. At the top, and at <50% of the range, the gate
    // stays shut — the AC is "scrolled ≥50%", not "≥50% visible".
    scrollTo(0, 300, 1000);
    expect(screen.getByTestId("continue-audio").props.accessibilityState.disabled).toBe(true);
    scrollTo(300, 300, 1000); // 300/700 ≈ 0.43 < 0.5
    expect(screen.getByTestId("continue-audio").props.accessibilityState.disabled).toBe(true);

    scrollTo(400, 300, 1000); // 400/700 ≈ 0.57 ≥ 0.5 → unlocked
    const after = screen.getByTestId("continue-audio");
    expect(after.props.accessibilityState.disabled).toBe(false);

    // US-006: "Continue to audio" now opens the estimate modal — it does NOT synthesize directly.
    fireEvent.press(after);
    expect(onProceed).not.toHaveBeenCalled();
    fireEvent.press(await screen.findByTestId("confirm-generate"));
    await waitFor(() =>
      expect(onProceed).toHaveBeenCalledWith(SCRIPT_RESPONSE.script, expect.any(Function)),
    );
  });

  it("does not trap the user when the script fits without scrolling", async () => {
    renderPreview();
    const scroll = await screen.findByTestId("script-scroll");
    fireEvent(scroll, "layout", { nativeEvent: { layout: { height: 500 } } });
    fireEvent(scroll, "contentSizeChange", 300, 200); // content shorter than viewport
    expect(screen.getByTestId("continue-audio").props.accessibilityState.disabled).toBe(false);
  });

  it("surfaces an audio failure inside the confirm modal (with retry)", async () => {
    const onProceed = jest.fn().mockRejectedValue(new Error("tts 502"));
    renderPreview({ onProceed });
    await screen.findByTestId("continue-audio");
    scrollTo(400, 300, 1000); // unlock
    fireEvent.press(screen.getByTestId("continue-audio"));
    fireEvent.press(await screen.findByTestId("confirm-generate"));
    expect(await screen.findByTestId("generate-error")).toHaveTextContent(/tts 502/);
    expect(screen.getByTestId("retry-generate")).toBeTruthy();
  });

  it("regenerates the script without changing components, re-gating the scroll", async () => {
    renderPreview();
    await screen.findByTestId("script-text");
    expect(scriptCalls()).toBe(1);
    const firstBody = fetchMock.mock.calls.find((c) => String(c[0]).endsWith("/script"))?.[1]?.body;

    // Unlock, then regenerate must re-lock the audio gate.
    scrollTo(400, 300, 1000);
    expect(screen.getByTestId("continue-audio").props.accessibilityState.disabled).toBe(false);

    fireEvent.press(screen.getByTestId("regenerate"));
    await waitFor(() => expect(scriptCalls()).toBe(2));

    const lastBody = fetchMock.mock.calls.filter((c) => String(c[0]).endsWith("/script")).at(-1)?.[1]?.body;
    expect(lastBody).toEqual(firstBody); // same components → unchanged
    await waitFor(() =>
      expect(screen.getByTestId("continue-audio").props.accessibilityState.disabled).toBe(true),
    );
  });
});
