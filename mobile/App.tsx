import { useState } from "react";
import { Pressable, SafeAreaView, StyleSheet, Text, View } from "react-native";
import { StatusBar } from "expo-status-bar";
import BriefingScreen from "./screens/BriefingScreen";
import TasksScreen from "./screens/TasksScreen";
import RemindersScreen from "./screens/RemindersScreen";
import CoursesScreen from "./screens/CoursesScreen";
import { colors } from "./lib/styles";

const TABS = [
  { key: "briefing", label: "Briefing", Screen: BriefingScreen },
  { key: "tasks", label: "Tasks", Screen: TasksScreen },
  { key: "reminders", label: "Reminders", Screen: RemindersScreen },
  { key: "courses", label: "Courses", Screen: CoursesScreen },
] as const;

export default function App() {
  const [activeTab, setActiveTab] = useState<(typeof TABS)[number]["key"]>("briefing");
  const ActiveScreen = TABS.find((t) => t.key === activeTab)!.Screen;

  return (
    <SafeAreaView style={styles.container}>
      {/* Conditionally mounting one screen at a time means switching tabs
          remounts the screen, which doubles as a "refresh on focus". */}
      <ActiveScreen />
      <View style={styles.tabBar}>
        {TABS.map((tab) => (
          <Pressable key={tab.key} style={styles.tabItem} onPress={() => setActiveTab(tab.key)}>
            <Text style={[styles.tabLabel, activeTab === tab.key && styles.tabLabelActive]}>{tab.label}</Text>
          </Pressable>
        ))}
      </View>
      <StatusBar style="auto" />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  tabBar: {
    flexDirection: "row",
    borderTopWidth: 1,
    borderTopColor: colors.border,
    backgroundColor: colors.surface,
  },
  tabItem: { flex: 1, alignItems: "center", paddingVertical: 12 },
  tabLabel: { fontSize: 13, color: colors.muted },
  tabLabelActive: { color: colors.accent, fontWeight: "700" },
});
