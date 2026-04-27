import { AppShell } from "@/components/layout/AppShell";
import { ChatWorkspace } from "@/components/chat/ChatWorkspace";

export default function Home() {
  return (
    <AppShell>
      <ChatWorkspace />
    </AppShell>
  );
}
