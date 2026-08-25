import React from "react";
import { View, Text, StyleSheet } from "react-native";
import { colors, fonts, radii, spacing } from "../theme/tokens";

export default function StreakTracker({ streak, activeToday }) {
  return (
    <View style={styles.card}>
      <Text style={styles.count}>{streak}</Text>
      <Text style={styles.label}>{streak === 1 ? "day streak" : "day streak"}</Text>
      <Text style={[styles.status, activeToday && styles.statusActive]}>
        {activeToday ? "practiced today" : "not yet today"}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: radii.lg,
    backgroundColor: colors.ink,
    padding: spacing.lg,
    alignItems: "center",
  },
  count: { fontFamily: fonts.display, fontSize: 40, color: "#fff" },
  label: { fontSize: 12, color: "rgba(255,255,255,0.6)", marginTop: 2 },
  status: { fontFamily: fonts.mono, fontSize: 10, letterSpacing: 0.5, color: colors.muted, marginTop: 10 },
  statusActive: { color: colors.living },
});
