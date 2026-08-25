import React from "react";
import { View, Text, StyleSheet, Pressable } from "react-native";
import { colors, fonts, radii, spacing } from "../theme/tokens";
import { usePlayVerseAudio } from "../voice/useVersePlayer";
import { speakAnswer } from "../voice/useVoice";

export default function RitualStepCard({ stepIndex, stepCount, instruction, mantra, onConfirm, confirming }) {
  const playVerseAudio = usePlayVerseAudio();

  return (
    <View style={styles.card}>
      <Text style={styles.stepTag}>STEP {stepIndex + 1} OF {stepCount}</Text>
      <Text style={styles.instruction}>{instruction}</Text>

      {mantra && (
        <View style={styles.mantraBox}>
          <Text style={styles.mantraSanskrit}>{mantra.sanskrit_text}</Text>
          <View style={styles.mantraRow}>
            <Text style={styles.mantraCite}>{mantra.citation.toUpperCase()}</Text>
            <Pressable
              onPress={() => (mantra.audio_url ? playVerseAudio(mantra.audio_url) : speakAnswer(mantra.sanskrit_text))}
              hitSlop={8}
            >
              <Text style={styles.speakIcon}>🔊</Text>
            </Pressable>
          </View>
        </View>
      )}

      <Pressable style={styles.doneButton} onPress={onConfirm} disabled={confirming}>
        <Text style={styles.doneButtonText}>{confirming ? "…" : "✓ done, next step"}</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: radii.lg,
    backgroundColor: colors.panel,
    borderWidth: 1,
    borderColor: colors.line,
    padding: spacing.lg,
  },
  stepTag: { fontFamily: fonts.mono, fontSize: 10, letterSpacing: 1, color: colors.muted, marginBottom: 10 },
  instruction: { fontFamily: fonts.display, fontSize: 19, lineHeight: 27, color: colors.ink, marginBottom: 18 },
  mantraBox: {
    backgroundColor: "#fff",
    borderRadius: radii.md,
    borderWidth: 1,
    borderColor: colors.line,
    padding: 14,
    marginBottom: 18,
  },
  mantraSanskrit: { fontFamily: fonts.displayItalic, fontSize: 16, lineHeight: 24, color: colors.ink, marginBottom: 8 },
  mantraRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  mantraCite: { fontSize: 11, letterSpacing: 0.5, color: colors.muted, fontFamily: fonts.bodyBold },
  speakIcon: { fontSize: 14, opacity: 0.6 },
  doneButton: {
    borderRadius: radii.pill,
    paddingVertical: 14,
    alignItems: "center",
    backgroundColor: colors.living,
  },
  doneButtonText: { color: "#fff", fontSize: 14, fontFamily: fonts.bodyBold },
});
