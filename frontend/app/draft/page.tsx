import { DraftPanel } from "@/components/draft-panel";
import { PageShell } from "@/components/page-shell";

export default function DraftPage() {
  return (
    <PageShell
      eyebrow="Feature 3"
      title="Generate first drafts that feel like a junior lawyer did the groundwork."
      description="Describe the matter in plain language, choose the document type, and generate a structured legal draft with the sections Indian lawyers expect."
    >
      <DraftPanel />
    </PageShell>
  );
}
