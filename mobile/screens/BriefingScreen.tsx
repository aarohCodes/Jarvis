import { useEffect, useState } from "react";
import { RefreshControl, ScrollView, Text, View } from "react-native";
import { api, Briefing } from "../lib/api";
import { shared } from "../lib/styles";

// No navigation library here — App.tsx swaps tabs by conditionally mounting
// one screen at a time, so mounting IS the "focus" event; a plain
// mount-time fetch is all that's needed to refresh when switching back.
export default function BriefingScreen() {
  const [briefing, setBriefing] = useState<Briefing | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    api
      .get<Briefing>("/briefing/morning")
      .then(setBriefing)
      .catch((e) => setError(e.message));
  }, []);

  const onRefresh = () => {
    setRefreshing(true);
    setError(null);
    api
      .get<Briefing>("/briefing/morning")
      .then(setBriefing)
      .catch((e) => setError(e.message))
      .finally(() => setRefreshing(false));
  };

  return (
    <ScrollView style={shared.screen} refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}>
      <Text style={shared.title}>Morning briefing</Text>
      {error && <Text style={shared.error}>{error}</Text>}

      <View style={shared.card}>
        <Text style={shared.cardTitle}>Next class</Text>
        {briefing?.next_class ? (
          <>
            <Text style={shared.rowTitle}>{briefing.next_class.title || briefing.next_class.course_code}</Text>
            <Text style={shared.rowSubtitle}>
              {briefing.next_class.start_time} – {briefing.next_class.end_time}
            </Text>
            <Text style={shared.rowSubtitle}>{briefing.next_class.location}</Text>
          </>
        ) : (
          <Text style={shared.empty}>No more classes today.</Text>
        )}
      </View>

      <View style={shared.card}>
        <Text style={shared.cardTitle}>Weather</Text>
        {briefing?.weather ? (
          <>
            <Text style={shared.rowTitle}>
              {briefing.weather.current_temp_c}°C — {briefing.weather.current_condition}
            </Text>
            <Text style={shared.rowSubtitle}>
              High {briefing.weather.high_temp_c}° / Low {briefing.weather.low_temp_c}°
            </Text>
          </>
        ) : (
          <Text style={shared.empty}>Set a home location in Preferences on the web dashboard.</Text>
        )}
      </View>

      <View style={shared.card}>
        <Text style={shared.cardTitle}>Due today</Text>
        {briefing?.assignments_due_today.length ? (
          briefing.assignments_due_today.map((a, i) => (
            <Text key={i} style={shared.rowTitle}>
              {a.title} {a.course ? `(${a.course})` : ""}
            </Text>
          ))
        ) : (
          <Text style={shared.empty}>Nothing due today.</Text>
        )}
      </View>

      <View style={shared.card}>
        <Text style={shared.cardTitle}>Open tasks</Text>
        {briefing?.open_tasks.length ? (
          briefing.open_tasks.map((t) => (
            <Text key={t.id} style={shared.rowTitle}>
              {t.title}
            </Text>
          ))
        ) : (
          <Text style={shared.empty}>No open tasks.</Text>
        )}
      </View>

      <View style={shared.card}>
        <Text style={shared.cardTitle}>Pending reminders</Text>
        {briefing?.pending_reminders.length ? (
          briefing.pending_reminders.map((r) => (
            <Text key={r.id} style={shared.rowTitle}>
              {r.text}
            </Text>
          ))
        ) : (
          <Text style={shared.empty}>No pending reminders.</Text>
        )}
      </View>
    </ScrollView>
  );
}
