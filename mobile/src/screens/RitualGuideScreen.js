// Phase 6: three states in one screen -- ritual list, materials/prep (shown
// upfront per architecture.md 2.3b step 3), then the live one-step-at-a-time
// session. Session state is server-side (ritual_sessions row), so this
// screen just reflects whatever step the backend says is current; a
// dropped connection and reopening the app resumes correctly via
// getRitualStep(sessionId).
import React, { useCallback, useState } from "react";
import { View, Text, StyleSheet, Pressable, FlatList, ActivityIndicator } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useFocusEffect } from "@react-navigation/native";
import { colors, fonts, radii, spacing } from "../theme/tokens";
import { listRituals, getRitual, startRitualSession, getRitualStep, confirmRitualStep, abandonRitualSession } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import RitualStepCard from "../components/RitualStepCard";

export default function RitualGuideScreen({ navigation }) {
  const { auth, isSignedIn } = useAuth();
  const [rituals, setRituals] = useState([]);
  const [detail, setDetail] = useState(null);
  const [session, setSession] = useState(null);
  const [step, setStep] = useState(null);
  const [confirming, setConfirming] = useState(false);

  useFocusEffect(
    useCallback(() => {
      listRituals().then(setRituals).catch(() => setRituals([]));
    }, [])
  );

  async function openRitual(r) {
    const full = await getRitual(r.ritual_id).catch(() => null);
    setDetail(full);
  }

  async function beginSession() {
    if (!isSignedIn || !detail) return;
    const s = await startRitualSession(detail.ritual_id, auth.token);
    setSession(s);
    const firstStep = await getRitualStep(s.session_id, auth.token);
    setStep(firstStep);
  }

  async function confirmStep() {
    if (!session) return;
    setConfirming(true);
    try {
      const next = await confirmRitualStep(session.session_id, auth.token);
      setStep(next);
    } finally {
      setConfirming(false);
    }
  }

  async function exitSession() {
    if (session && step && !step.complete) {
      await abandonRitualSession(session.session_id, auth.token).catch(() => {});
    }
    setSession(null);
    setStep(null);
    setDetail(null);
  }

  // Live session in progress
  if (session && step) {
    if (step.complete) {
      return (
        <SafeAreaView style={styles.container} edges={["top", "bottom"]}>
          <View style={styles.doneCenter}>
            <Text style={styles.doneTitle}>Ritual complete</Text>
            <Pressable style={styles.doneExit} onPress={exitSession}>
              <Text style={styles.doneExitText}>Back to rituals</Text>
            </Pressable>
          </View>
        </SafeAreaView>
      );
    }
    return (
      <SafeAreaView style={styles.container} edges={["top", "bottom"]}>
        <View style={styles.header}>
          <Pressable onPress={exitSession}>
            <Text style={styles.backText}>✕</Text>
          </Pressable>
          <Text style={styles.headerTitle}>{detail?.name}</Text>
        </View>
        <View style={{ padding: spacing.lg }}>
          <RitualStepCard
            stepIndex={step.current_step_index}
            stepCount={step.step_count}
            instruction={step.instruction}
            mantra={step.mantra}
            onConfirm={confirmStep}
            confirming={confirming}
          />
        </View>
      </SafeAreaView>
    );
  }

  // Materials/prep view, shown before the session starts
  if (detail) {
    return (
      <SafeAreaView style={styles.container} edges={["top", "bottom"]}>
        <View style={styles.header}>
          <Pressable onPress={() => setDetail(null)}>
            <Text style={styles.backText}>←</Text>
          </Pressable>
          <Text style={styles.headerTitle}>{detail.name}</Text>
        </View>
        <View style={{ padding: spacing.lg }}>
          {detail.tradition_region && <Text style={styles.variantTag}>{detail.tradition_region}</Text>}

          <Text style={styles.sectionLabel}>Materials needed</Text>
          {(detail.materials || []).map((m, i) => (
            <Text key={i} style={styles.materialRow}>
              • {m.item}{m.quantity ? ` — ${m.quantity}` : ""}{m.note ? ` (${m.note})` : ""}
            </Text>
          ))}

          {detail.preparation_steps?.length > 0 && (
            <>
              <Text style={styles.sectionLabel}>Before you begin</Text>
              {detail.preparation_steps.map((p, i) => (
                <Text key={i} style={styles.materialRow}>• {p}</Text>
              ))}
            </>
          )}

          <Pressable style={styles.startButton} onPress={beginSession} disabled={!isSignedIn}>
            <Text style={styles.startButtonText}>
              {isSignedIn ? "Gathered everything — begin" : "Sign in to begin"}
            </Text>
          </Pressable>
        </View>
      </SafeAreaView>
    );
  }

  // Ritual list
  return (
    <SafeAreaView style={styles.container} edges={["top", "bottom"]}>
      <View style={styles.header}>
        <Pressable onPress={() => navigation.goBack()}>
          <Text style={styles.backText}>←</Text>
        </Pressable>
        <Text style={styles.headerTitle}>Guided rituals</Text>
      </View>
      <FlatList
        data={rituals}
        keyExtractor={(r) => String(r.ritual_id)}
        contentContainerStyle={{ padding: spacing.lg, gap: 10 }}
        ListEmptyComponent={<Text style={styles.hint}>No rituals available yet.</Text>}
        renderItem={({ item }) => (
          <Pressable style={styles.ritualRow} onPress={() => openRitual(item)}>
            <Text style={styles.ritualName}>{item.name}</Text>
            {item.tradition_region && <Text style={styles.ritualRegion}>{item.tradition_region}</Text>}
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
  hint: { fontSize: 12, color: colors.muted, textAlign: "center" },
  ritualRow: {
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: radii.md,
    padding: 14,
    backgroundColor: "#fff",
  },
  ritualName: { fontFamily: fonts.bodyBold, fontSize: 14, color: colors.ink },
  ritualRegion: { fontSize: 11, color: colors.muted, marginTop: 3 },
  variantTag: {
    alignSelf: "flex-start",
    fontFamily: fonts.mono,
    fontSize: 10,
    letterSpacing: 0.5,
    color: colors.living,
    borderWidth: 1,
    borderColor: colors.living,
    borderRadius: 8,
    paddingHorizontal: 8,
    paddingVertical: 3,
    marginBottom: 16,
  },
  sectionLabel: { fontFamily: fonts.bodyBold, fontSize: 12, color: colors.ink, marginTop: 16, marginBottom: 8 },
  materialRow: { fontSize: 13, color: colors.inkSoft, lineHeight: 20 },
  startButton: {
    marginTop: 28,
    borderRadius: radii.pill,
    paddingVertical: 14,
    alignItems: "center",
    backgroundColor: colors.ink,
  },
  startButtonText: { color: "#fff", fontSize: 14, fontFamily: fonts.bodyBold },
  doneCenter: { flex: 1, alignItems: "center", justifyContent: "center", padding: spacing.lg },
  doneTitle: { fontFamily: fonts.display, fontSize: 22, color: colors.ink, marginBottom: 20 },
  doneExit: { borderRadius: radii.pill, paddingVertical: 12, paddingHorizontal: 24, backgroundColor: colors.ink },
  doneExitText: { color: "#fff", fontFamily: fonts.bodyBold, fontSize: 13 },
});
