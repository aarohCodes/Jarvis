import { redirect } from "next/navigation";

// The voice interface now lives on the command deck at "/" — this route
// is kept only so old links/bookmarks still land somewhere useful.
export default function ChatRedirect() {
  redirect("/");
}
