import React, { useCallback, useEffect, useState } from "react";
import { View, Text, StyleSheet, Pressable, FlatList, ActivityIndicator } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useFocusEffect } from "@react-navigation/native";
import { useAudioRecorder, RecordingPresets, AudioModule, setAudioModeAsync } from "expo-audio";
import { colors, fonts, radii, spacing } from "../theme/tokens";
import { listLessons, submitAttempt, logPractice } from "../api/client";
import { usePlayVerseAudio } from "../voice/useVersePlayer";
import { useAuth } from "../auth/AuthContext";

export default function PronunciationScreen({ navigation }) {
  const { auth, isSignedIn } = useAuth();
  const [lessons, setLessons] = useState([]);
  const [selected, setSelected] = useState(null);
  const [result, setResult] = useState(null);
  const [scoring, setScoring] = useState(false);
  const recorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY);
  const playReference = usePlayVerseAudio();

  useFocusEffect(
    useCallback(() => {
      listLessons().then(setLessons).catch(() => setLessons([]));
    }, [])
  );

  useEffect(() => {
    AudioModule.requestRecordingPermissionsAsync().then((status) => {
      if (status.granted) setAudioModeAsync({ playsInSilentMode: true, allowsRecording: true });
    });
  }, []);

  async function startRecording() {
    setResult(null);
    await recorder.prepareToRecordAsync();
    recorder.record();
  }

  async function stopAndScore() {
    await recorder.stop();
    if (!recorder.uri || !isSignedIn) return;
    setScoring(true);
    try {
      const scored = await submitAttempt(selected.lesson_id, recorder.uri, auth.token);
      setResult(scored);
    } catch (err) {
      setResult({ error: "Could not score that attempt. Please try again." });
    } finally {
      setScoring(false);
    }
  }

  if (selected) {
    return (
      <SafeAreaView style={styles.container} edges={["top", "bottom"]}>
        <View style={styles.header}>
          <Pressable onPress={() => { setSelected(null); setResult(null); }}>
            <Text style={styles.backText}>←</Text>
          </Pressable>
          <Text style={styles.headerTitle}>
            {selected.scripture} {selected.chapter}.{selected.verse_number}
          </Text>
        </View>

        <View style={styles.lessonBody}>
          <Text style={styles.sanskrit}>{selected.sanskrit_text}</Text>
          <Text style={styles.transliteration}>{selected.transliteration}</Text>

          <Pressable
            style={[styles.refButton, !selected.reference_audio_url && styles.refButtonDisabled]}
            onPress={() => playReference(selected.reference_audio_url)}
            disabled={!selected.reference_audio_url}
          >
            <Text style={styles.refButtonText}>
              {selected.reference_audio_url ? "▶ hear correct pronunciation" : "reference audio not ready yet"}
            </Text>
          </Pressable>

          <Pressable
            style={[styles.recordButton, recorder.isRecording && styles.recordButtonActive]}
            onPress={recorder.isRecording ? stopAndScore : startRecording}
            disabled={scoring || !isSignedIn}
          >
            <Text style={styles.recordButtonText}>
              {recorder.isRecording ? "● stop and score" : "🎤 record your attempt"}
            </Text>
          </Pressable>
          {!isSignedIn && <Text style={styles.hint}>Sign in to practice and track your streak.</Text>}

          {scoring && <ActivityIndicator color={colors.living} style={{ marginTop: 16 }} />}

          {result && !result.error && (
            <View style={styles.resultCard}>
              <Text style={styles.scoreText}>{result.score}/100</Text>
              <View style={styles.syllableRow}>
                {result.phoneme_feedback.map((f, i) => (
                  <Text key={i} style={[styles.syllable, !f.correct && styles.syllableWrong]}>
                    {f.syllable}
                  </Text>
                ))}
              </View>
            </View>
          )}
          {result?.error && <Text style={styles.hint}>{result.error}</Text>}
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container} edges={["top", "bottom"]}>
      <View style={styles.header}>
        <Pressable onPress={() => navigation.goBack()}>
          <Text style={styles.backText}>←</Text>
        </Pressable>
        <Text style={styles.headerTitle}>Practice pronunciation</Text>
      </View>
      <FlatList
        data={lessons}
        keyExtractor={(l) => String(l.lesson_id)}
        contentContainerStyle={{ padding: spacing.lg, gap: 10 }}
        ListEmptyComponent={<Text style={styles.hint}>No lessons available yet.</Text>}
        renderItem={({ item }) => (
          <Pressable style={styles.lessonRow} onPress={() => setSelected(item)}>
            <Text style={styles.lessonCite}>
              {item.scripture} {item.chapter}.{item.verse_number}
            </Text>
            <Text style={styles.lessonSanskrit} numberOfLines={1}>{item.sanskrit_text}</Text>
          </Pressable>
        )}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.white },
  header: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.line,
  },
  backText: { fontSize: 20, color: colors.ink },
  headerTitle: { fontFamily: fonts.bodyBold, fontSize: 15, color: colors.ink },
  lessonRow: {
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: radii.md,
    padding: 14,
    backgroundColor: "#fff",
  },
  lessonCite: { fontSize: 11, color: colors.muted, fontFamily: fonts.bodyBold, marginBottom: 4 },
  lessonSanskrit: { fontFamily: fonts.displayItalic, fontSize: 15, color: colors.ink },
  lessonBody: { padding: spacing.lg },
  sanskrit: { fontFamily: fonts.displayItalic, fontSize: 20, lineHeight: 30, color: colors.ink, marginBottom: 10 },
  transliteration: { fontFamily: fonts.mono, fontSize: 13, color: colors.inkSoft, marginBottom: 24 },
  refButton: {
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: radii.pill,
    paddingVertical: 12,
    alignItems: "center",
    marginBottom: 12,
    backgroundColor: "#fff",
  },
  refButtonDisabled: { opacity: 0.5 },
  refButtonText: { fontSize: 13, color: colors.inkSoft, fontFamily: fonts.bodyMedium },
  recordButton: {
    borderRadius: radii.pill,
    paddingVertical: 14,
    alignItems: "center",
    backgroundColor: colors.ink,
  },
  recordButtonActive: { backgroundColor: colors.living },
  recordButtonText: { color: "#fff", fontSize: 14, fontFamily: fonts.bodyBold },
  hint: { fontSize: 12, color: colors.muted, textAlign: "center", marginTop: 12 },
  resultCard: {
    marginTop: 20,
    padding: 16,
    borderRadius: radii.md,
    backgroundColor: colors.panel,
    alignItems: "center",
  },
  scoreText: { fontFamily: fonts.display, fontSize: 32, color: colors.ink, marginBottom: 10 },
  syllableRow: { flexDirection: "row", flexWrap: "wrap", gap: 6, justifyContent: "center" },
  syllable: {
    fontFamily: fonts.mono,
    fontSize: 13,
    color: colors.ink,
    backgroundColor: "#fff",
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
  },
  syllableWrong: { color: colors.living, borderWidth: 1, borderColor: colors.living },
});
