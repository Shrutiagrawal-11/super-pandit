import React, { useCallback, useState } from "react";
import { View, Text, StyleSheet, FlatList, Pressable, ActivityIndicator } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useFocusEffect } from "@react-navigation/native";
import { colors, fonts, radii, spacing } from "../theme/tokens";
import { useAuth } from "../auth/AuthContext";
import { listSaved, unsaveVerse } from "../api/client";

export default function SavedScreen({ navigation }) {
  const { auth, isSignedIn } = useAuth();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  useFocusEffect(
    useCallback(() => {
      if (!isSignedIn) {
        setLoading(false);
        return;
      }
      setLoading(true);
      listSaved(auth.token)
        .then(setItems)
        .catch(() => setItems([]))
        .finally(() => setLoading(false));
    }, [isSignedIn, auth?.token])
  );

  async function handleRemove(verseId) {
    setItems((prev) => prev.filter((i) => i.verse_id !== verseId));
    unsaveVerse(verseId, auth.token).catch(() => {});
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Pressable style={styles.backButton} onPress={() => navigation.goBack()}>
          <Text style={styles.backText}>←</Text>
        </Pressable>
        <Text style={styles.title}>Saved</Text>
      </View>

      {!isSignedIn ? (
        <View style={styles.emptyState}>
          <Text style={styles.emptyTitle}>Sign in to save verses</Text>
          <Text style={styles.empty}>Saved verses sync to your account and are here whenever you come back.</Text>
          <Pressable style={styles.signInButton} onPress={() => navigation.navigate("Auth")}>
            <Text style={styles.signInText}>Sign in</Text>
          </Pressable>
        </View>
      ) : loading ? (
        <ActivityIndicator color={colors.living} style={{ marginTop: 40 }} />
      ) : items.length === 0 ? (
        <View style={styles.emptyState}>
          <Text style={styles.empty}>Nothing saved yet. Verses you save from a conversation will show up here.</Text>
        </View>
      ) : (
        <FlatList
          data={items}
          keyExtractor={(item) => String(item.verse_id)}
          contentContainerStyle={{ padding: spacing.lg, gap: 12 }}
          renderItem={({ item }) => (
            <View style={styles.card}>
              <View style={styles.cardHead}>
                <Text style={styles.cite}>
                  {item.scripture.toUpperCase()} {item.chapter}.{item.verse_number}
                </Text>
                <Pressable onPress={() => handleRemove(item.verse_id)}>
                  <Text style={styles.remove}>remove</Text>
                </Pressable>
              </View>
              <Text style={styles.verse}>{item.sanskrit_text}</Text>
              {item.note && <Text style={styles.note}>{item.note}</Text>}
            </View>
          )}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.white },
  header: { flexDirection: "row", alignItems: "center", gap: 12, padding: spacing.lg },
  backButton: {},
  backText: { fontSize: 20, color: colors.ink },
  title: { fontFamily: fonts.display, fontSize: 20, color: colors.ink },
  emptyState: { flex: 1, alignItems: "center", justifyContent: "center", padding: spacing.lg, gap: 10 },
  emptyTitle: { fontFamily: fonts.bodyBold, fontSize: 15, color: colors.ink },
  empty: { fontFamily: fonts.body, fontSize: 13, color: colors.muted, textAlign: "center", lineHeight: 20, maxWidth: 260 },
  signInButton: { backgroundColor: colors.ink, borderRadius: radii.pill, paddingVertical: 12, paddingHorizontal: 28, marginTop: 8 },
  signInText: { color: "#fff", fontFamily: fonts.bodyBold, fontSize: 14 },
  card: { borderWidth: 1, borderColor: colors.line, borderRadius: radii.md, padding: 16, backgroundColor: colors.panel },
  cardHead: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 8 },
  cite: { fontFamily: fonts.mono, fontSize: 11, color: colors.muted },
  remove: { fontFamily: fonts.body, fontSize: 11, color: colors.living },
  verse: { fontFamily: fonts.displayItalic, fontSize: 15, color: colors.ink, lineHeight: 22 },
  note: { fontFamily: fonts.body, fontSize: 12, color: colors.inkSoft, marginTop: 8 },
});
