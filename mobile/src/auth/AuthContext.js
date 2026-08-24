import React, { createContext, useContext, useEffect, useState } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";
import * as api from "../api/client";

const AuthContext = createContext(null);
const STORAGE_KEY = "pandit_auth";

export function AuthProvider({ children }) {
  const [auth, setAuth] = useState(null); // null while loading, {} if guest, {token,userId,displayName} if signed in
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    AsyncStorage.getItem(STORAGE_KEY)
      .then((raw) => setAuth(raw ? JSON.parse(raw) : {}))
      .catch(() => setAuth({}))
      .finally(() => setLoading(false));
  }, []);

  async function persist(next) {
    setAuth(next);
    await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  }

  async function signIn(email, password) {
    const result = await api.login(email, password);
    await persist({ token: result.token, userId: result.user_id, displayName: result.display_name });
  }

  async function signUp(email, password, displayName) {
    const result = await api.signup(email, password, displayName);
    await persist({ token: result.token, userId: result.user_id, displayName: result.display_name });
  }

  async function signOut() {
    await persist({});
  }

  const isSignedIn = Boolean(auth?.token);

  return (
    <AuthContext.Provider value={{ auth, loading, isSignedIn, signIn, signUp, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
