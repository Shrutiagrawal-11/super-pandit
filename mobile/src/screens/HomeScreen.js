import React, { useCallback, useState } from "react";
import { View, Text, StyleSheet, ScrollView, Pressable } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useFocusEffect } from "@react-navigation/native";
import { colors, fonts, radii, spacing } from "../theme/tokens";
import { useAuth } from "../auth/AuthContext";
import { getProgress, listChapters } from "../api/client";

function greetingForHour() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  if (h < 21) return "Good evening";
  return "Good night";
}

const MANTRAS = [
  { name: "Gāyatrī", sub: "morning · 3 min" },
  { name: "Śānti Mantra", sub: "closing" },
  { name: "Mahāmṛtyuñjaya", sub: "protection" },
];

export default function HomeScreen({ navigation }) {
  const { auth, isSignedIn } = useAuth();
  const [progress, setProgress] = useState(null);
  const [chapters, setChapters] = useState([]);

  useFocusEffect(
    useCallback(() => {
      if (!isSignedIn) {
        setProgress(null);
        return;
      }
      getProgress(auth.token)
        .then((rows) => setProgress(rows[0] || null))
        .catch(() => setProgress(null));
    }, [isSignedIn, auth?.token])
  );

  useFocusEffect(
    useCallback(() => {
      listChapters().then(setChapters).catch(() => setChapters([]));
    }, [])
  );

  return (
    <SafeAreaView style={styles.container} edges={["top"]}>
      <ScrollView contentContainerStyle={{ paddingBottom: 110 }}>
        <View style={styles.top}>
          <View>
            <Text style={styles.greet}>{greetingForHour()}</Text>
            <Text style={styles.topTitle}>Where shall we begin?</Text>
          </View>
          <View style={styles.avatar}>
            <Text style={{ fontFamily: fonts.display, fontSize: 15 }}>॥</Text>
          </View>
        </View>

        {isSignedIn && progress ? (
          <Pressable style={styles.readyCard} onPress={() => navigation.navigate("Chat")}>
            <Text style={styles.readyTag}>resume where you left off</Text>
            <Text style={styles.readyVerse}>
              {progress.scripture}, Chapter {progress.chapter}, Verse {progress.verse_number}
            </Text>
            <View style={styles.readyRow}>
              <Text style={styles.readyCite}>
                {progress.scripture.toUpperCase()} {progress.chapter}.{progress.verse_number}
              </Text>
              <View style={styles.goCircle}>
                <Text style={{ color: "#fff" }}>↗</Text>
              </View>
            </View>
          </Pressable>
        ) : !isSignedIn ? (
          <Pressable style={styles.readyCard} onPress={() => navigation.navigate("Auth")}>
            <Text style={styles.readyTag}>browsing as a guest</Text>
            <Text style={styles.readyVerse}>Sign in to save verses and resume where you left off.</Text>
            <View style={styles.readyRow}>
              <Text style={styles.readyCite}>SIGN IN</Text>
              <View style={styles.goCircle}>
                <Text style={{ color: "#fff" }}>↗</Text>
              </View>
            </View>
          </Pressable>
        ) : null}

        {isSignedIn && (
          <View style={styles.practiceRow}>
            <Pressable style={styles.practiceCard} onPress={() => navigation.navigate("Practice")}>
              <Text style={styles.practiceLabel}>Daily practice</Text>
              <Text style={styles.practiceGo}>↗</Text>
            </Pressable>
            <Pressable style={styles.practiceCard} onPress={() => navigation.navigate("Pronunciation")}>
              <Text style={styles.practiceLabel}>Pronunciation</Text>
              <Text style={styles.practiceGo}>↗</Text>
            </Pressable>
          </View>
        )}

        <Section title="Mantras of the Day" more="see all">
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.hrow}>
            {MANTRAS.map((m) => (
              <View key={m.name} style={styles.clip}>
                <View style={styles.playDot}>
                  <Text style={{ fontSize: 11 }}>▶</Text>
                </View>
                <Text style={styles.clipName}>{m.name}</Text>
                <Text style={styles.clipSub}>{m.sub}</Text>
              </View>
            ))}
          </ScrollView>
        </Section>

        {chapters.length > 0 && (
          <Section title="By Chapter" more={`${chapters.length} available`}>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.hrow}>
              {chapters.map((c) => (
                <View key={`${c.scripture}-${c.chapter}`} style={styles.chapter}>
                  <View style={styles.chapterThumb}>
                    <Text style={styles.chapterNum}>CH {String(c.chapter).padStart(2, "0")}</Text>
                  </View>
                  <View style={{ padding: 10 }}>
                    <Text style={styles.chapterName}>{c.scripture}</Text>
                    <Text style={styles.chapterVerses}>{c.verse_count} verses</Text>
                  </View>
                </View>
              ))}
            </ScrollView>
          </Section>
        )}
      </ScrollView>

      <View style={styles.tabbar}>
        <TabItem label="Home" active />
        <TabItem label="Chat" onPress={() => navigation.navigate("Chat")} />
        <Pressable style={styles.askTab} onPress={() => navigation.navigate("Chat")}>
          <View style={styles.askCircle}>
            <Text style={{ color: "#fff", fontSize: 16 }}>॥</Text>
            <View style={styles.askDot} />
          </View>
        </Pressable>
        <TabItem label="Saved" onPress={() => navigation.navigate("Saved")} />
        <TabItem label="You" onPress={() => navigation.navigate("Profile")} />
      </View>
    </SafeAreaView>
  );
}

function Section({ title, more, children }) {
  return (
    <View style={{ marginBottom: 24 }}>
      <View style={styles.sectionHead}>
        <Text style={styles.sectionTitle}>{title}</Text>
        <Text style={styles.sectionMore}>{more}</Text>
      </View>
      {children}
    </View>
  );
}

function TabItem({ label, active, onPress }) {
  return (
    <Pressable style={styles.tab} onPress={onPress}>
      <Text style={[styles.tabLabel, active && styles.tabLabelActive]}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.white },
  top: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.md,
    paddingBottom: 6,
  },
  greet: { fontSize: 12, color: colors.muted, marginBottom: 3 },
  topTitle: { fontFamily: fonts.display, fontSize: 20, color: colors.ink },
  avatar: {
    width: 38,
    height: 38,
    borderRadius: 19,
    backgroundColor: colors.panel,
    borderWidth: 1,
    borderColor: colors.line,
    alignItems: "center",
    justifyContent: "center",
  },
  readyCard: {
    margin: spacing.lg,
    borderRadius: radii.lg,
    backgroundColor: colors.ink,
    padding: 20,
  },
  readyTag: {
    fontFamily: fonts.mono,
    fontSize: 10,
    letterSpacing: 1,
    textTransform: "uppercase",
    color: colors.livingDim,
    marginBottom: 10,
  },
  readyVerse: {
    fontFamily: fonts.displayItalic,
    fontSize: 17,
    lineHeight: 25,
    color: "#fff",
    marginBottom: 14,
  },
  readyRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  readyCite: { fontSize: 11, color: "rgba(255,255,255,0.55)", letterSpacing: 0.5 },
  goCircle: {
    width: 34,
    height: 34,
    borderRadius: 17,
    backgroundColor: colors.living,
    alignItems: "center",
    justifyContent: "center",
  },
  practiceRow: { flexDirection: "row", gap: 11, paddingHorizontal: spacing.lg, marginBottom: 24 },
  practiceCard: {
    flex: 1,
    borderRadius: radii.md,
    borderWidth: 1,
    borderColor: colors.line,
    backgroundColor: "#fff",
    padding: 14,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  practiceLabel: { fontSize: 12, fontFamily: fonts.bodyBold, color: colors.ink },
  practiceGo: { fontSize: 14, color: colors.muted },
  sectionHead: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "baseline",
    paddingHorizontal: spacing.lg,
    marginBottom: 12,
  },
  sectionTitle: { fontSize: 14, fontFamily: fonts.bodyBold, color: colors.ink },
  sectionMore: { fontFamily: fonts.mono, fontSize: 10, color: colors.muted },
  hrow: { paddingHorizontal: spacing.lg, gap: 11 },
  clip: {
    width: 108,
    height: 150,
    borderRadius: radii.md,
    backgroundColor: colors.panel,
    borderWidth: 1,
    borderColor: colors.line,
    padding: 10,
    justifyContent: "space-between",
  },
  playDot: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: colors.line,
    alignItems: "center",
    justifyContent: "center",
    alignSelf: "center",
    marginTop: 30,
  },
  clipName: { fontFamily: fonts.displayItalic, fontSize: 13, color: colors.ink },
  clipSub: { fontSize: 10, color: colors.muted },
  chapter: {
    width: 156,
    borderRadius: radii.sm + 4,
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: colors.line,
    overflow: "hidden",
  },
  chapterThumb: { height: 84, backgroundColor: colors.panel, justifyContent: "flex-end", padding: 9 },
  chapterNum: { fontFamily: fonts.mono, fontSize: 10, fontWeight: "700", color: colors.inkSoft },
  chapterName: { fontSize: 12, fontFamily: fonts.bodyBold, color: colors.ink, marginBottom: 2 },
  chapterVerses: { fontSize: 10, color: colors.muted },
  tabbar: {
    position: "absolute",
    left: 0,
    right: 0,
    bottom: 0,
    flexDirection: "row",
    justifyContent: "space-around",
    alignItems: "flex-end",
    paddingVertical: 12,
    paddingBottom: 24,
    backgroundColor: "rgba(255,255,255,0.94)",
    borderTopWidth: 1,
    borderTopColor: colors.line,
  },
  tab: { alignItems: "center", width: 56 },
  tabLabel: { fontSize: 10, color: colors.muted, fontFamily: fonts.bodyMedium },
  tabLabelActive: { color: colors.ink },
  askTab: { marginTop: -24 },
  askCircle: {
    width: 46,
    height: 46,
    borderRadius: 23,
    backgroundColor: colors.ink,
    alignItems: "center",
    justifyContent: "center",
  },
  askDot: {
    position: "absolute",
    top: 6,
    right: 6,
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: colors.living,
  },
});
