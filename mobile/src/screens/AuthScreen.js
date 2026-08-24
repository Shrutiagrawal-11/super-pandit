import React, { useState } from "react";
import { View, Text, StyleSheet, TextInput, Pressable, ActivityIndicator } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { colors, fonts, radii, spacing } from "../theme/tokens";
import { useAuth } from "../auth/AuthContext";

export default function AuthScreen({ navigation }) {
  const { signIn, signUp } = useAuth();
  const [mode, setMode] = useState("login"); // "login" | "signup"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  function validate() {
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) return "Enter a valid email address";
    if (mode === "signup" && password.length < 8) return "Password must be at least 8 characters";
    if (!password) return "Enter your password";
    return null;
  }

  async function submit() {
    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }
    setError(null);
    setBusy(true);
    try {
      if (mode === "login") {
        await signIn(email.trim(), password);
      } else {
        await signUp(email.trim(), password, displayName.trim() || null);
      }
      navigation.goBack();
    } catch (err) {
      setError(err.message || "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  return (
    <SafeAreaView style={styles.container}>
      <Pressable style={styles.backButton} onPress={() => navigation.goBack()}>
        <Text style={styles.backText}>←</Text>
      </Pressable>

      <Text style={styles.title}>{mode === "login" ? "Welcome back" : "Create an account"}</Text>
      <Text style={styles.sub}>Saved verses and reading progress sync when you're signed in.</Text>

      {mode === "signup" && (
        <TextInput
          style={styles.input}
          placeholder="Name"
          placeholderTextColor={colors.muted}
          value={displayName}
          onChangeText={setDisplayName}
        />
      )}
      <TextInput
        style={styles.input}
        placeholder="Email"
        placeholderTextColor={colors.muted}
        value={email}
        onChangeText={setEmail}
        autoCapitalize="none"
        keyboardType="email-address"
      />
      <TextInput
        style={styles.input}
        placeholder="Password"
        placeholderTextColor={colors.muted}
        value={password}
        onChangeText={setPassword}
        secureTextEntry
      />

      {error && <Text style={styles.error}>{error}</Text>}

      <Pressable style={styles.submitButton} onPress={submit} disabled={busy}>
        {busy ? <ActivityIndicator color="#fff" /> : (
          <Text style={styles.submitText}>{mode === "login" ? "Sign in" : "Sign up"}</Text>
        )}
      </Pressable>

      <Pressable onPress={() => setMode(mode === "login" ? "signup" : "login")}>
        <Text style={styles.switchText}>
          {mode === "login" ? "New here? Create an account" : "Already have an account? Sign in"}
        </Text>
      </Pressable>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.white, padding: spacing.lg },
  backButton: { marginBottom: 12 },
  backText: { fontSize: 20, color: colors.ink },
  title: { fontFamily: fonts.display, fontSize: 24, color: colors.ink, marginBottom: 6 },
  sub: { fontFamily: fonts.body, fontSize: 13, color: colors.muted, marginBottom: 24, lineHeight: 19 },
  input: {
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: radii.sm,
    paddingHorizontal: 16,
    paddingVertical: 14,
    fontFamily: fonts.body,
    fontSize: 14,
    color: colors.ink,
    marginBottom: 12,
  },
  error: { color: colors.living, fontSize: 13, marginBottom: 12, fontFamily: fonts.body },
  submitButton: {
    backgroundColor: colors.ink,
    borderRadius: radii.pill,
    paddingVertical: 15,
    alignItems: "center",
    marginTop: 8,
    marginBottom: 18,
  },
  submitText: { color: "#fff", fontFamily: fonts.bodyBold, fontSize: 15 },
  switchText: { textAlign: "center", color: colors.inkSoft, fontFamily: fonts.body, fontSize: 13 },
});
