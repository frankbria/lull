import { Platform } from "react-native";
import { createAudioPlayer } from "expo-audio";
// SDK 54 moved the classic file API (cacheDirectory/writeAsStringAsync) to the /legacy entry;
// the new default export is the File/Directory API. Legacy is the minimal change here.
import * as FileSystem from "expo-file-system/legacy";
import { apiBase } from "./apiBase";

// Synthesize a script to audio and start playback in the chosen voice (US-005). Returns a cleanup
// function the caller runs on unmount/next-run — expo-audio's imperative players don't auto-release,
// and web Blob URLs leak.
// ponytail: a fresh guest token per call keeps the no-auth dev loop working; real sign-in + a
// persisted session land with the auth UI. On-device playback hardening is #24.
export async function synthesizeAndPlay(
  scriptText: string,
  personaId?: string,
): Promise<() => void> {
  const base = apiBase();

  // Generation is gated; claim a guest token for the one free generation (no auth UI yet).
  const gres = await fetch(`${base}/auth/guest`, { method: "POST" });
  if (!gres.ok) throw new Error(`/auth/guest ${gres.status}`);
  const { guest_token } = await gres.json();

  const tres = await fetch(`${base}/tts`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Guest-Token": guest_token },
    body: JSON.stringify({ text: scriptText, persona_id: personaId }),
  });
  if (!tres.ok) throw new Error(`/tts ${tres.status}`);
  return playResponse(tres, "session");
}

// Play a persona's short preview clip (US-005/FR-V2). The preview endpoint is ungated, so it costs
// no free generation — no guest token needed. Returns the same cleanup contract as synthesizeAndPlay.
export async function playVoicePreview(personaId: string): Promise<() => void> {
  const tres = await fetch(`${apiBase()}/voices/${personaId}/preview`);
  if (!tres.ok) throw new Error(`/voices/${personaId}/preview ${tres.status}`);
  return playResponse(tres, "preview");
}

// Decode an audio response and start playback, returning the cleanup function. Honor the server's
// container: stub returns WAV, ElevenLabs returns MP3. Mislabeling the bytes (e.g. MP3 as .wav) can
// fail to decode on web/iOS — derive extension + MIME from the Content-Type.
async function playResponse(res: Response, label: string): Promise<() => void> {
  const contentType = res.headers.get("content-type") ?? "audio/mpeg";
  const bytes = new Uint8Array(await res.arrayBuffer());
  const uri = await audioUri(bytes, contentType, label);
  const player = createAudioPlayer(uri);
  player.play();
  return () => {
    player.remove();
    if (Platform.OS === "web") URL.revokeObjectURL(uri);
  };
}

// Map the /tts Content-Type to a file extension the player can decode by name (iOS/web care).
function audioExt(contentType: string): "wav" | "mp3" {
  return contentType.includes("wav") ? "wav" : "mp3";
}

// Web (expo-file-system is native-only): play straight from a Blob URL.
// Native: write the bytes to the cache as base64 and play the file. `label` keeps the session and
// preview clips in separate cache files so one can't clobber the other mid-playback.
async function audioUri(bytes: Uint8Array, contentType: string, label: string): Promise<string> {
  if (Platform.OS === "web") {
    // Uint8Array is a valid BlobPart at runtime; cast past TS 5.9's stricter ArrayBuffer typing.
    const blob = new Blob([bytes as BlobPart], { type: contentType });
    return URL.createObjectURL(blob);
  }
  const uri = `${FileSystem.cacheDirectory}lull-${label}.${audioExt(contentType)}`;
  await FileSystem.writeAsStringAsync(uri, base64FromBytes(bytes), {
    encoding: FileSystem.EncodingType.Base64,
  });
  return uri;
}

const B64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

export function base64FromBytes(bytes: Uint8Array): string {
  let out = "";
  for (let i = 0; i < bytes.length; i += 3) {
    const b0 = bytes[i];
    const b1 = bytes[i + 1] ?? 0;
    const b2 = bytes[i + 2] ?? 0;
    out += B64[b0 >> 2];
    out += B64[((b0 & 3) << 4) | (b1 >> 4)];
    out += i + 1 < bytes.length ? B64[((b1 & 15) << 2) | (b2 >> 6)] : "=";
    out += i + 2 < bytes.length ? B64[b2 & 63] : "=";
  }
  return out;
}
