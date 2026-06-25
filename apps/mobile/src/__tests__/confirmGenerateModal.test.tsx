import { fireEvent, render, screen, waitFor } from "@testing-library/react-native";
import { ConfirmGenerateModal, estimateGenerationSeconds } from "../ConfirmGenerateModal";

const REPORT = {
  script: "Make yourself comfortable.",
  char_count: 1200,
  est_seconds: 130, // 2:10
  est_cost_usd: 0.02,
  components: {},
};

function renderModal(
  overrides: { onGenerate?: jest.Mock; onClose?: jest.Mock } = {},
) {
  const onGenerate = overrides.onGenerate ?? jest.fn().mockResolvedValue(undefined);
  const onClose = overrides.onClose ?? jest.fn();
  render(<ConfirmGenerateModal report={REPORT} onGenerate={onGenerate} onClose={onClose} />);
  return { onGenerate, onClose };
}

describe("ConfirmGenerateModal (US-006)", () => {
  it("shows estimated characters, audio length, and generation time before generating", () => {
    renderModal();
    expect(screen.getByTestId("est-chars")).toHaveTextContent(/1,?200/);
    expect(screen.getByTestId("est-length")).toHaveTextContent(/2:10/);
    // Whatever the heuristic, it must render a non-empty estimate.
    expect(screen.getByTestId("est-gen-time")).toHaveTextContent(/\d/);
  });

  it("requires an explicit 'Confirm and Generate' tap before generating", async () => {
    const { onGenerate } = renderModal();
    expect(onGenerate).not.toHaveBeenCalled();
    fireEvent.press(screen.getByTestId("confirm-generate"));
    await waitFor(() => expect(onGenerate).toHaveBeenCalledTimes(1));
  });

  it("walks through the script → voice → finalize progress stages", async () => {
    const onGenerate = jest.fn((onProgress: (s: string) => void) => {
      onProgress("script");
      onProgress("voice");
      return new Promise<void>(() => {}); // stay pending so the generating UI is observable
    });
    renderModal({ onGenerate });
    fireEvent.press(screen.getByTestId("confirm-generate"));

    expect(await screen.findByTestId("stage-voice")).toBeTruthy();
    expect(screen.getByTestId("stage-voice").props.accessibilityState.selected).toBe(true);
    expect(screen.getByTestId("stage-script").props.accessibilityState.selected).toBe(false);
    expect(screen.getByTestId("stage-finalize").props.accessibilityState.selected).toBe(false);
    // No confirm button while a generation is in flight.
    expect(screen.queryByTestId("confirm-generate")).toBeNull();
  });

  it("surfaces an error and retries, dismissing on the eventual success", async () => {
    const onGenerate = jest
      .fn()
      .mockRejectedValueOnce(new Error("/tts 502"))
      .mockResolvedValueOnce(undefined);
    const { onClose } = renderModal({ onGenerate });

    fireEvent.press(screen.getByTestId("confirm-generate"));
    expect(await screen.findByTestId("generate-error")).toHaveTextContent(/502/);

    fireEvent.press(screen.getByTestId("retry-generate"));
    await waitFor(() => expect(onGenerate).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(onClose).toHaveBeenCalled()); // success dismisses the modal
  });

  it("ignores Android back while a generation is in flight", async () => {
    const onGenerate = jest.fn(() => new Promise<void>(() => {})); // stays pending
    const { onClose } = renderModal({ onGenerate });
    fireEvent.press(screen.getByTestId("confirm-generate"));
    await screen.findByTestId("progress");
    fireEvent(screen.getByTestId("confirm-modal"), "requestClose"); // Android back
    expect(onClose).not.toHaveBeenCalled();
  });

  it("estimateGenerationSeconds grows with length and has a sane floor", () => {
    expect(estimateGenerationSeconds(0)).toBeGreaterThan(0);
    expect(estimateGenerationSeconds(2000)).toBeGreaterThan(estimateGenerationSeconds(200));
  });
});
