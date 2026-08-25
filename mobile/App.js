import React from "react";
import { View, ActivityIndicator } from "react-native";
import { StatusBar } from "expo-status-bar";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { SafeAreaProvider } from "react-native-safe-area-context";

import { useFonts as useFraunces, Fraunces_600SemiBold, Fraunces_500Medium_Italic } from "@expo-google-fonts/fraunces";
import { useFonts as useManrope, Manrope_400Regular, Manrope_600SemiBold, Manrope_700Bold } from "@expo-google-fonts/manrope";
import { useFonts as useJetBrainsMono, JetBrainsMono_500Medium } from "@expo-google-fonts/jetbrains-mono";

import OpenScreen from "./src/screens/OpenScreen";
import HomeScreen from "./src/screens/HomeScreen";
import ChatScreen from "./src/screens/ChatScreen";
import SavedScreen from "./src/screens/SavedScreen";
import ProfileScreen from "./src/screens/ProfileScreen";
import AuthScreen from "./src/screens/AuthScreen";
import PronunciationScreen from "./src/screens/PronunciationScreen";
import PracticeTrackerScreen from "./src/screens/PracticeTrackerScreen";
import { AuthProvider, useAuth } from "./src/auth/AuthContext";
import { colors } from "./src/theme/tokens";

const Stack = createNativeStackNavigator();

function LoadingScreen() {
  return (
    <View style={{ flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: colors.white }}>
      <ActivityIndicator color={colors.living} />
    </View>
  );
}

function Navigator() {
  // Gate the whole navigator behind AsyncStorage resolving, so no screen
  // ever briefly renders as "guest" before a real signed-in session loads.
  const { loading } = useAuth();
  if (loading) return <LoadingScreen />;

  return (
    <NavigationContainer>
      <StatusBar style="dark" />
      <Stack.Navigator initialRouteName="Open" screenOptions={{ headerShown: false }}>
        <Stack.Screen name="Open" component={OpenScreen} />
        <Stack.Screen name="Home" component={HomeScreen} />
        <Stack.Screen name="Chat" component={ChatScreen} />
        <Stack.Screen name="Saved" component={SavedScreen} />
        <Stack.Screen name="Profile" component={ProfileScreen} />
        <Stack.Screen name="Auth" component={AuthScreen} />
        <Stack.Screen name="Pronunciation" component={PronunciationScreen} />
        <Stack.Screen name="Practice" component={PracticeTrackerScreen} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}

export default function App() {
  const [frauncesLoaded] = useFraunces({ Fraunces_600SemiBold, Fraunces_500Medium_Italic });
  const [manropeLoaded] = useManrope({ Manrope_400Regular, Manrope_600SemiBold, Manrope_700Bold });
  const [monoLoaded] = useJetBrainsMono({ JetBrainsMono_500Medium });

  if (!frauncesLoaded || !manropeLoaded || !monoLoaded) {
    return <LoadingScreen />;
  }

  return (
    <SafeAreaProvider>
      <AuthProvider>
        <Navigator />
      </AuthProvider>
    </SafeAreaProvider>
  );
}
