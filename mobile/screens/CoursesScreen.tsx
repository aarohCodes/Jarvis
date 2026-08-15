import { useEffect, useState } from "react";
import { FlatList, Text, View } from "react-native";
import { api, Course } from "../lib/api";
import { shared } from "../lib/styles";

export default function CoursesScreen() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.get<Course[]>("/courses/schedule").then(setCourses).catch((e) => setError(e.message));
  }, []);

  return (
    <View style={shared.screen}>
      <Text style={shared.title}>Courses</Text>
      {error && <Text style={shared.error}>{error}</Text>}
      <Text style={[shared.empty, { marginBottom: 12 }]}>
        Read-only here — add or edit sections on the web dashboard.
      </Text>

      <FlatList
        data={courses}
        keyExtractor={(c) => c.id}
        ListEmptyComponent={<Text style={shared.empty}>No courses added yet.</Text>}
        renderItem={({ item }) => (
          <View style={shared.card}>
            <Text style={shared.rowTitle}>
              {item.course_code.toUpperCase()}.{item.section} — {item.title || "Untitled"}
            </Text>
            <Text style={shared.rowSubtitle}>
              {item.days || "—"} {item.start_time && item.end_time ? `· ${item.start_time}–${item.end_time}` : ""}
            </Text>
            {item.location && <Text style={shared.rowSubtitle}>{item.location}</Text>}
          </View>
        )}
      />
    </View>
  );
}
