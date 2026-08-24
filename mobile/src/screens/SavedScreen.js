import React from "react";
import { View, Text, StyleSheet } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { colors, fonts, spacing } from "../theme/tokens";

export default function SavedScreen() {
  return (
    <SafeAreaView style={styles.container}>
      <Text style={styles.title}>Saved</Text>
      <Text style={styles.empty}>Verses and answers you save will show up here.</Text>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.white, padding: spacing.lg },
  title: { fontFamily: fonts.display, fontSize: 22, color: colors.ink, marginBottom: 12, marginTop: 8 },
  empty: { fontFamily: fonts.body, fontSize: 14, color: colors.muted, lineHeight: 21 },
});
