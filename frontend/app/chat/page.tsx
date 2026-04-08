import { ChatPanel } from "@/components/chat-panel";
import { PageShell } from "@/components/page-shell";

export default function ChatPage() {
  return (
    <PageShell
      eyebrow="Feature 1"
      title="Research faster with citation-aware Indian legal retrieval."
      description="The chat flow embeds the lawyer's question, searches the vector database, sends the top legal chunks to the model, and returns a grounded answer with case references."
    >
      <ChatPanel />
    </PageShell>
  );
}
