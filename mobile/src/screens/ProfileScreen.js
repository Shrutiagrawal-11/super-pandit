import React from "react";
import { View, Text, StyleSheet, Pressable } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { colors, fonts, radii, spacing } from "../theme/tokens";
import { useAuth } from "../auth/AuthContext";

export default function ProfileScreen({ navigation }) {
  const { auth, isSignedIn, signOut } = useAuth();

  return (
    <SafeAreaView style={styles.container}>
      <Pressable style={styles.backButton} onPress={() => navigation.goBack()}>
        <Text style={styles.backText}>←</Text>
      </Pressable>

      <View style={styles.avatar}>
        <Text style={{ fontFamily: fonts.display, fontSize: 20 }}>॥</Text>
      </View>

      {isSignedIn ? (
        <>
          <Text style={styles.title}>{auth.displayName || "Your account"}</Text>
          <Text style={styles.sub}>Signed in</Text>
          <Pressable style={styles.signOutButton} onPress={signOut}>
            <Text style={styles.signOutText}>Sign out</Text>
          </Pressable>
        </>
      ) : (
        <>
          <Text style={styles.title}>You're browsing as a guest</Text>
          <Text style={styles.sub}>Sign in to save verses and pick up where you left off.</Text>
          <Pressable style={styles.signInButton} onPress={() => navigation.navigate("Auth")}>
            <Text style={styles.signInText}>Sign in</Text>
          </Pressable>
        </>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.white, alignItems: "center", padding: spacing.lg, paddingTop: 20 },
  backButton: { alignSelf: "flex-start", marginBottom: 24 },
  backText: { fontSize: 20, color: colors.ink },
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
  title: { fontFamily: fonts.display, fontSize: 20, color: colors.ink, marginBottom: 6, textAlign: "center" },
  sub: { fontFamily: fonts.body, fontSize: 13, color: colors.muted, textAlign: "center", lineHeight: 20, marginBottom: 20 },
  signInButton: { backgroundColor: colors.ink, borderRadius: radii.pill, paddingVertical: 13, paddingHorizontal: 30 },
  signInText: { color: "#fff", fontFamily: fonts.bodyBold, fontSize: 14 },
  signOutButton: { borderWidth: 1, borderColor: colors.line, borderRadius: radii.pill, paddingVertical: 13, paddingHorizontal: 30 },
  signOutText: { color: colors.ink, fontFamily: fonts.bodyBold, fontSize: 14 },
});
