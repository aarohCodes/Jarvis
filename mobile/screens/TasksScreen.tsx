import { useEffect, useState } from "react";
import { FlatList, Pressable, Text, TextInput, View } from "react-native";
import { api, Task } from "../lib/api";
import { shared } from "../lib/styles";

export default function TasksScreen() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [title, setTitle] = useState("");

  const load = () => api.get<Task[]>("/tasks?status=open").then(setTasks).catch((e) => setError(e.message));

  useEffect(() => {
    load();
  }, []);

  const addTask = async () => {
    if (!title.trim()) return;
    setError(null);
    try {
      await api.post("/tasks", { title });
      setTitle("");
      load();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const complete = async (id: string) => {
    await api.put(`/tasks/${id}`, { status: "completed" });
    load();
  };

  const remove = async (id: string) => {
    await api.del(`/tasks/${id}`);
    load();
  };

  return (
    <View style={shared.screen}>
      <Text style={shared.title}>Tasks</Text>
      {error && <Text style={shared.error}>{error}</Text>}

      <TextInput style={shared.input} placeholder="New task" value={title} onChangeText={setTitle} onSubmitEditing={addTask} returnKeyType="done" />
      <Pressable style={[shared.button, { marginBottom: 16 }]} onPress={addTask}>
        <Text style={shared.buttonText}>Add task</Text>
      </Pressable>

      <FlatList
        data={tasks}
        keyExtractor={(t) => t.id}
        ListEmptyComponent={<Text style={shared.empty}>No open tasks.</Text>}
        renderItem={({ item }) => (
          <View style={shared.card}>
            <Text style={shared.rowTitle}>{item.title}</Text>
            {item.due_at && <Text style={shared.rowSubtitle}>{new Date(item.due_at).toLocaleString()}</Text>}
            <View style={{ flexDirection: "row", gap: 12, marginTop: 8 }}>
              <Pressable onPress={() => complete(item.id)}>
                <Text style={{ color: "#16a34a", fontWeight: "600" }}>Complete</Text>
              </Pressable>
              <Pressable onPress={() => remove(item.id)}>
                <Text style={{ color: "#dc2626", fontWeight: "600" }}>Delete</Text>
              </Pressable>
            </View>
          </View>
        )}
      />
    </View>
  );
}
