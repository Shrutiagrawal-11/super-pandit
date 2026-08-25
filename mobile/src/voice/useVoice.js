// Phase 3 voice: STT via the phone's built-in speech recognizer
// (expo-speech-recognition), TTS via Expo's built-in expo-speech.
// Requires a dev build (EAS or `npx expo run:*`) — Expo Go can't load
// custom native modules, so isAvailable() below guards against crashing
// there per OPERATIONS.md's Expo Go-based testing flow.
import { useCallback, useEffect, useState } from "react";
import * as Speech from "expo-speech";
import {
  ExpoSpeechRecognitionModule,
  useSpeechRecognitionEvent,
} from "expo-speech-recognition";

export function isVoiceAvailable() {
  return !!ExpoSpeechRecognitionModule?.start;
}

export function useVoiceInput(onFinalResult) {
  const [listening, setListening] = useState(false);

  useSpeechRecognitionEvent("start", () => setListening(true));
  useSpeechRecognitionEvent("end", () => setListening(false));
  useSpeechRecognitionEvent("error", () => setListening(false));
  useSpeechRecognitionEvent("result", (event) => {
    const text = event.results?.[0]?.transcript;
    if (text && event.isFinal) onFinalResult(text);
  });

  const start = useCallback(async () => {
    if (!isVoiceAvailable()) return;
    const perm = await ExpoSpeechRecognitionModule.requestPermissionsAsync();
    if (!perm.granted) return;
    ExpoSpeechRecognitionModule.start({ lang: "en-US", interimResults: false });
  }, []);

  const stop = useCallback(() => {
    if (!isVoiceAvailable()) return;
    ExpoSpeechRecognitionModule.stop();
  }, []);

  return { listening, start, stop };
}

// English explanation only, never the Sanskrit verse — mispronounced
// Sanskrit from a generic TTS voice would violate the app's pronunciation
// trust bar (architecture.md Section on voice flow). Sanskrit is spoken
// only via pre-rendered, scholar-reviewed audio (see api/client.js
// verse.audio_url), never synthesized live.
export function speakAnswer(text) {
  Speech.stop();
  Speech.speak(text, { language: "en-US", pitch: 1.0, rate: 0.95 });
}

export function stopSpeaking() {
  Speech.stop();
}

export function useIsSpeaking() {
  const [speaking, setSpeaking] = useState(false);
  useEffect(() => {
    const id = setInterval(() => {
      Speech.isSpeakingAsync().then(setSpeaking);
    }, 300);
    return () => clearInterval(id);
  }, []);
  return speaking;
}
