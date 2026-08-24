import React, { useMemo, useRef, useState } from "react";
import { View, Text, StyleSheet, Pressable, Animated } from "react-native";
import { colors, fonts, radii } from "../theme/tokens";

function timeGreeting() {
  const h = new Date().getHours();
  if (h < 5) return "It's quiet where you are.\nGood, this is a good time to sit with it.";
  if (h < 12) return "Good morning.\nA guide to the scriptures, grounded in the text itself.";
  if (h < 17) return "Good afternoon.\nA guide to the scriptures, grounded in the text itself.";
  if (h < 21) return "Good evening.\nA guide to the scriptures, grounded in the text itself.";
  return "It's late.\nStill here, if you need something.";
}

export default function OpenScreen({ navigation }) {
  const greeting = useMemo(() => timeGreeting(), []);
  const [rippleKey, setRippleKey] = useState(0);
  const rippleScale = useRef(new Animated.Value(0)).current;
  const rippleOpacity = useRef(new Animated.Value(0)).current;
  const fillWidth = useRef(new Animated.Value(0)).current;
  const holdTimer = useRef(null);

  function ringMark() {
    rippleScale.setValue(0);
    rippleOpacity.setValue(0.85);
    setRippleKey((k) => k + 1);
    Animated.parallel([
      Animated.timing(rippleScale, { toValue: 1, duration: 900, useNativeDriver: true }),
      Animated.timing(rippleOpacity, { toValue: 0, duration: 900, useNativeDriver: true }),
    ]).start();
  }

  function startCharge() {
    Animated.timing(fillWidth, { toValue: 1, duration: 250, useNativeDriver: false }).start();
    holdTimer.current = setTimeout(() => {
      navigation.replace("Home");
    }, 250);
  }

  function cancelCharge() {
    if (holdTimer.current) {
      clearTimeout(holdTimer.current);
      holdTimer.current = null;
    }
    Animated.timing(fillWidth, { toValue: 0, duration: 150, useNativeDriver: false }).start();
  }

  return (
    <View style={styles.container}>
      <Pressable onPress={ringMark} style={styles.markZone}>
        <Text style={styles.mark}>॥ Pandit</Text>
        <Animated.View
          key={rippleKey}
          pointerEvents="none"
          style={[
            styles.ripple,
            {
              opacity: rippleOpacity,
              transform: [{ scale: rippleScale.interpolate({ inputRange: [0, 1], outputRange: [0.05, 12] }) }],
            },
          ]}
        />
        <Text style={styles.hint}>tap to hear it ring</Text>
      </Pressable>

      <Text style={styles.line}>{greeting}</Text>

      <Pressable
        onPressIn={startCharge}
        onPressOut={cancelCharge}
        style={styles.enterButton}
      >
        <Animated.View
          style={[
            styles.enterFill,
            {
              width: fillWidth.interpolate({ inputRange: [0, 1], outputRange: ["0%", "100%"] }),
            },
          ]}
        />
        <View style={styles.dot} />
        <Text style={styles.enterText} selectable={false}>Hold to Begin</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.white,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 24,
  },
  markZone: {
    alignItems: "center",
    padding: 30,
  },
  mark: {
    fontFamily: fonts.display,
    fontSize: 40,
    color: colors.ink,
  },
  ripple: {
    position: "absolute",
    top: "50%",
    left: "50%",
    width: 14,
    height: 14,
    marginLeft: -7,
    marginTop: -7,
    borderRadius: 7,
    borderWidth: 1.5,
    borderColor: colors.living,
  },
  hint: {
    marginTop: 8,
    fontFamily: fonts.mono,
    fontSize: 10,
    letterSpacing: 1,
    textTransform: "uppercase",
    color: colors.muted,
  },
  line: {
    marginTop: 20,
    fontFamily: fonts.displayItalic,
    fontSize: 17,
    color: colors.inkSoft,
    textAlign: "center",
    maxWidth: 260,
    lineHeight: 26,
  },
  enterButton: {
    position: "absolute",
    bottom: 64,
    flexDirection: "row",
    alignItems: "center",
    gap: 9,
    paddingVertical: 15,
    paddingHorizontal: 28,
    borderRadius: radii.pill,
    borderWidth: 1.5,
    borderColor: colors.ink,
    backgroundColor: colors.white,
    overflow: "hidden",
  },
  enterFill: {
    position: "absolute",
    left: 0,
    top: 0,
    bottom: 0,
    backgroundColor: colors.living,
  },
  dot: {
    width: 7,
    height: 7,
    borderRadius: 3.5,
    backgroundColor: colors.living,
  },
  enterText: {
    fontFamily: fonts.bodyBold,
    fontSize: 14,
    color: colors.ink,
  },
});
