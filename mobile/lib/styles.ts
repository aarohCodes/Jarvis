import { StyleSheet } from "react-native";

export const colors = {
  bg: "#f7f7f8",
  surface: "#ffffff",
  border: "#e2e2e5",
  text: "#1a1a1e",
  muted: "#6b6b73",
  accent: "#4f46e5",
  danger: "#dc2626",
  success: "#16a34a",
};

export const shared = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg, padding: 16 },
  title: { fontSize: 22, fontWeight: "700", color: colors.text, marginBottom: 12 },
  card: {
    backgroundColor: colors.surface,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 14,
    marginBottom: 12,
  },
  cardTitle: { fontSize: 12, fontWeight: "600", color: colors.muted, textTransform: "uppercase", marginBottom: 6 },
  rowTitle: { fontSize: 15, fontWeight: "600", color: colors.text },
  rowSubtitle: { fontSize: 13, color: colors.muted, marginTop: 2 },
  empty: { color: colors.muted, fontSize: 14 },
  error: { color: colors.danger, fontSize: 14, marginBottom: 12 },
  input: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 8,
    padding: 10,
    fontSize: 15,
    marginBottom: 8,
    backgroundColor: colors.surface,
    color: colors.text,
  },
  button: {
    backgroundColor: colors.accent,
    borderRadius: 8,
    paddingVertical: 10,
    alignItems: "center",
  },
  buttonText: { color: "#fff", fontWeight: "600", fontSize: 15 },
  divider: { height: 1, backgroundColor: colors.border, marginVertical: 8 },
});
