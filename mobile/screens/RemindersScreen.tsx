import { useEffect, useState } from "react";
import { FlatList, Pressable, Text, TextInput, View } from "react-native";
import { api, Reminder } from "../lib/api";
import { shared } from "../lib/styles";

export default function RemindersScreen() {
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [text, setText] = useState("");
  const [remindAt, setRemindAt] = useState("");

  const load = () => api.get<Reminder[]>("/reminders?status=pending").then(setReminders).catch((e) => setError(e.message));

  useEffect(() => {
    load();
  }, []);

  const addReminder = async () => {
    if (!text.trim() || !remindAt.trim()) return;
    setError(null);
    try {
      const parsed = new Date(remindAt);
      if (isNaN(parsed.getTime())) throw new Error("Couldn't parse that date/time.");
      await api.post("/reminders", { text, remind_at: parsed.toISOString() });
      setText("");
      setRemindAt("");
      load();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const remove = async (id: string) => {
    await api.del(`/reminders/${id}`);
    load();
  };

  return (
    <View style={shared.screen}>
      <Text style={shared.title}>Reminders</Text>
      {error && <Text style={shared.error}>{error}</Text>}

      <TextInput style={shared.input} placeholder="Remind me about..." value={text} onChangeText={setText} />
      {/* No native date picker dependency added yet — type a parseable date/time.
          Add @react-native-community/datetimepicker later for a real picker UI. */}
      <TextInput style={shared.input} placeholder="2026-08-20 21:30" value={remindAt} onChangeText={setRemindAt} />
      <Pressable style={[shared.button, { marginBottom: 16 }]} onPress={addReminder}>
        <Text style={shared.buttonText}>Add reminder</Text>
      </Pressable>

      <FlatList
        data={reminders}
        keyExtractor={(r) => r.id}
        ListEmptyComponent={<Text style={shared.empty}>No pending reminders.</Text>}
        renderItem={({ item }) => (
          <View style={shared.card}>
            <Text style={shared.rowTitle}>{item.text}</Text>
            <Text style={shared.rowSubtitle}>{new Date(item.remind_at).toLocaleString()}</Text>
            <Pressable onPress={() => remove(item.id)} style={{ marginTop: 8 }}>
              <Text style={{ color: "#dc2626", fontWeight: "600" }}>Delete</Text>
            </Pressable>
          </View>
        )}
      />
    </View>
  );
}
