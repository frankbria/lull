/**
 * US-008 local device cache: an identical (script, voice) render replays from the device file
 * cache and skips the /tts round trip; the cache key is content-addressed.
 */
import { Platform } from "react-native";
import { synthesizeAndPlay, trackCacheKey } from "../audio";

// Mock the native audio + file-system seams so the cache logic runs in node without a device.
// `mock`-prefixed names are the only out-of-scope refs jest.mock factories allow.
const mockFileExists = { value: false };
jest.mock("expo-audio", () => ({
  createAudioPlayer: () => ({ play: jest.fn(), remove: jest.fn() }),
}));
jest.mock("expo-file-system/legacy", () => ({
  cacheDirectory: "file:///cache/",
  EncodingType: { Base64: "base64" },
  getInfoAsync: jest.fn(async () => ({ exists: mockFileExists.value })),
  writeAsStringAsync: jest.fn(async () => undefined),
}));

describe("trackCacheKey", () => {
  it("is deterministic and sensitive to script and voice", () => {
    expect(trackCacheKey("relax", "aria")).toBe(trackCacheKey("relax", "aria"));
    expect(trackCacheKey("relax", "aria")).not.toBe(trackCacheKey("relax", "james"));
    expect(trackCacheKey("relax", "aria")).not.toBe(trackCacheKey("drift", "aria"));
  });
});

describe("synthesizeAndPlay device cache (native)", () => {
  beforeAll(() => {
    Platform.OS = "ios"; // exercise the native file-cache path
  });
  beforeEach(() => {
    mockFileExists.value = false;
    jest.restoreAllMocks();
  });

  function mockFetchAudio() {
    const fetchMock = jest.fn(async (url: string) => {
      if (url.endsWith("/auth/guest")) {
        return { ok: true, json: async () => ({ guest_token: "g" }) } as Response;
      }
      // /tts
      return {
        ok: true,
        headers: { get: () => "audio/wav" },
        arrayBuffer: async () => new Uint8Array([1, 2, 3]).buffer,
      } as unknown as Response;
    });
    global.fetch = fetchMock as unknown as typeof global.fetch;
    return fetchMock;
  }

  it("fetches /tts on a cache miss", async () => {
    const fetchMock = mockFetchAudio();
    const cleanup = await synthesizeAndPlay("relax deeply", "aria");
    cleanup();
    const calls = fetchMock.mock.calls.map((c) => c[0] as string);
    expect(calls.some((u) => u.endsWith("/tts"))).toBe(true);
  });

  it("replays from cache and skips /tts when the file already exists", async () => {
    mockFileExists.value = true; // pretend an identical render is already cached on device
    const fetchMock = mockFetchAudio();
    const cleanup = await synthesizeAndPlay("relax deeply", "aria");
    cleanup();
    const calls = fetchMock.mock.calls.map((c) => c[0] as string);
    expect(calls.some((u) => u.endsWith("/tts"))).toBe(false);
    expect(calls.some((u) => u.endsWith("/auth/guest"))).toBe(false);
  });
});
