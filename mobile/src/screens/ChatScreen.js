import React, { useRef, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  Pressable,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { usePreventScreenCapture } from "expo-screen-capture";
import { colors, fonts, radii, spacing } from "../theme/tokens";
import { askPandit, saveVerse, setProgress } from "../api/client";
import { useAuth } from "../auth/AuthContext";

const SUGGESTIONS = ["fear of failure", "how do I stop overthinking?", "what is dharma?"];

let nextId = 1;

export default function ChatScreen({ navigation }) {
  usePreventScreenCapture(); // FLAG_SECURE on Android, screenshot/recording block on iOS — per PROJECT_PLAN.md Phase 2
  const { auth, isSignedIn } = useAuth();
  const [messages, setMessages] = useState([
    {
      id: nextId++,
      role: "pandit",
      text: "Ask me anything about the scriptures. I'll answer only from what's actually written and cited.",
    },
  ]);
  const [input, setInput] = useState("");
  const [thinking, setThinking] = useState(false);
  const listRef = useRef(null);

  async function ask(question) {
    if (!question.trim() || thinking) return;
    setInput("");
    setMessages((prev) => [...prev, { id: nextId++, role: "user", text: question }]);
    setThinking(true);

    try {
      const result = await askPandit(question);
      const verse = result.context_verses?.[0];
      setMessages((prev) => [
        ...prev,
        {
          id: nextId++,
          role: "pandit",
          text: result.answer,
          verse: verse ? verse.sanskrit_text : null,
          cite: verse ? `${verse.scripture} ${verse.chapter}.${verse.verse_number}` : null,
          verseId: verse ? verse.verse_id : null,
          saved: false,
        },
      ]);

      if (verse && isSignedIn) {
        setProgress(verse.scripture, verse.chapter, verse.verse_number, auth.token).catch(() => {});
      }
    } catch (err) {
      const text = err.message?.startsWith("The server is taking too long")
        ? err.message
        : "Something went wrong reaching the server. Please try again.";
      setMessages((prev) => [...prev, { id: nextId++, role: "pandit", text }]);
    } finally {
      setThinking(false);
    }
  }

  async function toggleSave(message) {
    if (!isSignedIn || !message.verseId) return;
    try {
      if (!message.saved) {
        await saveVerse(message.verseId, null, auth.token);
      }
      setMessages((prev) => prev.map((m) => (m.id === message.id ? { ...m, saved: true } : m)));
    } catch (err) {
      // saving is a nice-to-have, a failure here shouldn't interrupt the conversation
    }
  }

  return (
    <SafeAreaView style={styles.container} edges={["top", "bottom"]}>
      <View style={styles.header}>
        <Pressable
          style={styles.backButton}
          onPress={() => (navigation.canGoBack() ? navigation.goBack() : navigation.navigate("Home"))}
        >
          <Text style={styles.backText}>←</Text>
        </Pressable>
        <View style={styles.disc}>
          <Text style={{ color: "#fff", fontFamily: fonts.display }}>॥</Text>
          {thinking && <View style={styles.thinkRing} />}
        </View>
        <View>
          <Text style={styles.headerName}>Pandit</Text>
          <Text style={[styles.headerState, thinking && styles.headerStateActive]}>
            {thinking ? "reflecting…" : "here for the scriptures"}
          </Text>
        </View>
      </View>

      <FlatList
        ref={listRef}
        data={messages}
        keyExtractor={(m) => String(m.id)}
        contentContainerStyle={styles.thread}
        onContentSizeChange={() => listRef.current?.scrollToEnd({ animated: true })}
        renderItem={({ item }) => (
          <View style={[styles.bubble, item.role === "user" ? styles.bubbleUser : styles.bubblePandit]}>
            <Text style={item.role === "user" ? styles.userText : styles.panditText}>{item.text}</Text>
            {item.verse && (
              <Text style={styles.verse}>{item.verse}</Text>
            )}
            {item.cite && (
              <View style={styles.citeRow}>
                <Text style={styles.cite}>{item.cite.toUpperCase()}</Text>
                {isSignedIn && (
                  <Pressable onPress={() => toggleSave(item)}>
                    <Text style={[styles.saveIcon, item.saved && styles.saveIconActive]}>
                      {item.saved ? "♥ saved" : "♡ save"}
                    </Text>
                  </Pressable>
                )}
              </View>
            )}
          </View>
        )}
      />

      {thinking && (
        <View style={styles.typingRow}>
          <ActivityIndicator size="small" color={colors.living} />
        </View>
      )}

      <View style={styles.suggestions}>
        {SUGGESTIONS.map((s) => (
          <Pressable key={s} style={styles.chip} onPress={() => ask(s)}>
            <Text style={styles.chipText}>{s}</Text>
          </Pressable>
        ))}
      </View>

      <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <View style={styles.composer}>
          <TextInput
            style={styles.input}
            placeholder="Ask about a verse, a story, a feeling…"
            placeholderTextColor={colors.muted}
            value={input}
            onChangeText={setInput}
            onSubmitEditing={() => ask(input)}
            editable={!thinking}
          />
          <Pressable
            style={[styles.sendButton, thinking && styles.sendButtonDisabled]}
            disabled={thinking}
            onPress={() => ask(input)}
          >
            <Text style={{ color: "#fff", fontSize: 16 }}>↑</Text>
          </Pressable>
        </View>
      </KeyboardAvoidingView>
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
  backButton: { paddingRight: 4 },
  backText: { fontSize: 20, color: colors.ink },
  disc: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.ink,
    alignItems: "center",
    justifyContent: "center",
  },
  thinkRing: {
    position: "absolute",
    top: -3,
    left: -3,
    right: -3,
    bottom: -3,
    borderRadius: 21,
    borderWidth: 1.5,
    borderColor: colors.living,
  },
  headerName: { fontFamily: fonts.bodyBold, fontSize: 14, color: colors.ink },
  headerState: { fontSize: 11, color: colors.muted },
  headerStateActive: { color: colors.living },
  thread: { padding: spacing.lg, gap: 14 },
  bubble: { borderRadius: radii.md, padding: 14, maxWidth: "82%" },
  bubbleUser: { alignSelf: "flex-end", backgroundColor: colors.ink },
  bubblePandit: { alignSelf: "flex-start", backgroundColor: colors.panel, borderWidth: 1, borderColor: colors.line },
  userText: { color: "#fff", fontSize: 14, lineHeight: 21 },
  panditText: { color: colors.ink, fontSize: 14, lineHeight: 21 },
  verse: {
    fontFamily: fonts.displayItalic,
    fontSize: 15,
    color: colors.ink,
    marginTop: 8,
    marginBottom: 6,
    lineHeight: 22,
    borderLeftWidth: 2,
    borderLeftColor: colors.living,
    paddingLeft: 10,
  },
  cite: { fontSize: 11, letterSpacing: 0.5, color: colors.muted, fontFamily: fonts.bodyBold },
  citeRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  saveIcon: { fontSize: 11, color: colors.muted, fontFamily: fonts.bodyBold },
  saveIconActive: { color: colors.living },
  typingRow: { paddingHorizontal: spacing.lg, paddingBottom: 4 },
  suggestions: { flexDirection: "row", gap: 8, paddingHorizontal: spacing.lg, paddingBottom: 8, flexWrap: "wrap" },
  chip: {
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: 14,
    paddingVertical: 6,
    paddingHorizontal: 12,
    backgroundColor: "#fff",
  },
  chipText: { fontSize: 12, color: colors.inkSoft },
  composer: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    margin: spacing.lg,
    borderWidth: 1.5,
    borderColor: colors.line,
    borderRadius: radii.pill,
    paddingVertical: 6,
    paddingLeft: 20,
    paddingRight: 6,
    backgroundColor: "#fff",
  },
  input: { flex: 1, fontFamily: fonts.body, fontSize: 14, color: colors.ink, paddingVertical: 10 },
  sendButton: {
    width: 38,
    height: 38,
    borderRadius: 19,
    backgroundColor: colors.ink,
    alignItems: "center",
    justifyContent: "center",
  },
  sendButtonDisabled: { opacity: 0.35 },
});
