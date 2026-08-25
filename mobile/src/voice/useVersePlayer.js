// Plays pre-rendered, scholar-reviewed Sanskrit verse audio (Vagdhenu
// output, see OPERATIONS.md Section 8) from the backend's /verse_audio
// static mount. Only ever plays a URL the server confirmed exists
// (context_verses[].audio_url) — never live-synthesizes Sanskrit.
import { useRef, useCallback } from "react";
import { createAudioPlayer } from "expo-audio";
import { API_BASE_URL } from "../api/client";

export function usePlayVerseAudio() {
  const playerRef = useRef(null);

  const play = useCallback((audioUrl) => {
    if (!audioUrl) return;
    playerRef.current?.remove();
    const player = createAudioPlayer(`${API_BASE_URL}${audioUrl}`);
    playerRef.current = player;
    player.play();
  }, []);

  return play;
}
