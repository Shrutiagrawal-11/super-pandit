import React from "react";
import { View, Text, StyleSheet } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { colors, fonts, spacing } from "../theme/tokens";

export default function ProfileScreen() {
  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.avatar}>
        <Text style={{ fontFamily: fonts.display, fontSize: 20 }}>॥</Text>
      </View>
      <Text style={styles.title}>You</Text>
      <Text style={styles.empty}>Sign in to sync your saved verses and reading progress.</Text>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.white, alignItems: "center", padding: spacing.lg, paddingTop: 48 },
  avatar: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: colors.panel,
    borderWidth: 1,
    borderColor: colors.line,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 16,
  },
  title: { fontFamily: fonts.display, fontSize: 22, color: colors.ink, marginBottom: 8 },
  empty: { fontFamily: fonts.body, fontSize: 14, color: colors.muted, textAlign: "center", lineHeight: 21 },
});
