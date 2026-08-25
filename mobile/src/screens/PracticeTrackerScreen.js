import React, { useCallback, useState } from "react";
import { View, Text, StyleSheet, Pressable, FlatList } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useFocusEffect } from "@react-navigation/native";
import { colors, fonts, radii, spacing } from "../theme/tokens";
import { getTodayPrompt, getStreak, getPracticeHistory, logPractice } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import StreakTracker from "../components/StreakTracker";

export default function PracticeTrackerScreen({ navigation }) {
  const { auth, isSignedIn } = useAuth();
  const [prompt, setPrompt] = useState(null);
  const [streak, setStreak] = useState(null);
  const [history, setHistory] = useState([]);
  const [reflected, setReflected] = useState(false);

  useFocusEffect(
    useCallback(() => {
      getTodayPrompt().then(setPrompt).catch(() => setPrompt(null));
      if (!isSignedIn) return;
      getStreak(auth.token).then((s) => { setStreak(s); setReflected(s.active_today); }).catch(() => {});
      getPracticeHistory(auth.token).then(setHistory).catch(() => setHistory([]));
    }, [isSignedIn, auth?.token])
  );

  async function markReflected() {
    if (!isSignedIn || reflected) return;
    setReflected(true);
    try {
      await logPractice("daily_reflection", null, auth.token);
      const s = await getStreak(auth.token);
      setStreak(s);
    } catch (err) {
      setReflected(false);
    }
  }

  return (
    <SafeAreaView style={styles.container} edges={["top", "bottom"]}>
      <View style={styles.header}>
        <Pressable onPress={() => navigation.goBack()}>
          <Text style={styles.backText}>←</Text>
        </Pressable>
        <Text style={styles.headerTitle}>Daily practice</Text>
      </View>

      <FlatList
        data={history}
        keyExtractor={(h, i) => `${h.date}-${i}`}
        ListHeaderComponent={
          <View style={{ padding: spacing.lg, gap: spacing.lg }}>
            {isSignedIn && streak && <StreakTracker streak={streak.current_streak} activeToday={streak.active_today} />}
            {!isSignedIn && (
              <Text style={styles.hint}>Sign in to track your streak and practice history.</Text>
            )}

            {prompt && (
              <View style={styles.promptCard}>
                <Text style={styles.promptTag}>TODAY'S REFLECTION</Text>
                <Text style={styles.promptText}>{prompt.prompt}</Text>
                <Pressable
                  style={[styles.reflectButton, reflected && styles.reflectButtonDone]}
                  onPress={markReflected}
                  disabled={!isSignedIn || reflected}
                >
                  <Text style={styles.reflectButtonText}>{reflected ? "✓ done today" : "mark as reflected"}</Text>
                </Pressable>
              </View>
            )}

            {history.length > 0 && <Text style={styles.historyTitle}>Recent activity</Text>}
          </View>
        }
        contentContainerStyle={{ paddingBottom: spacing.xl }}
        renderItem={({ item }) => (
          <View style={styles.historyRow}>
            <Text style={styles.historyDate}>{item.date}</Text>
            <Text style={styles.historyType}>{item.activity_type.replace("_", " ")}</Text>
            {item.score != null && <Text style={styles.historyScore}>{Math.round(item.score)}</Text>}
          </View>
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
  hint: { fontSize: 12, color: colors.muted, textAlign: "center" },
  promptCard: {
    borderRadius: radii.lg,
    backgroundColor: colors.panel,
    borderWidth: 1,
    borderColor: colors.line,
    padding: spacing.lg,
  },
  promptTag: { fontFamily: fonts.mono, fontSize: 10, letterSpacing: 1, color: colors.muted, marginBottom: 8 },
  promptText: { fontFamily: fonts.displayItalic, fontSize: 16, lineHeight: 23, color: colors.ink, marginBottom: 16 },
  reflectButton: {
    borderRadius: radii.pill,
    paddingVertical: 12,
    alignItems: "center",
    backgroundColor: colors.ink,
  },
  reflectButtonDone: { backgroundColor: colors.living },
  reflectButtonText: { color: "#fff", fontSize: 13, fontFamily: fonts.bodyBold },
  historyTitle: { fontFamily: fonts.bodyBold, fontSize: 13, color: colors.ink },
  historyRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: spacing.lg,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: colors.line,
  },
  historyDate: { fontSize: 11, color: colors.muted, fontFamily: fonts.mono, flex: 1 },
  historyType: { fontSize: 12, color: colors.ink, flex: 1 },
  historyScore: { fontSize: 12, color: colors.living, fontFamily: fonts.bodyBold },
});
