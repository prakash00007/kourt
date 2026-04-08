import { PageShell } from "@/components/page-shell";
import { UploadPanel } from "@/components/upload-panel";

export default function UploadPage() {
  return (
    <PageShell
      eyebrow="Feature 2"
      title="Compress long judgments into the points lawyers actually need."
      description="Upload a Supreme Court or High Court PDF and get a structured summary that is easy to scan before advising a client, preparing arguments, or drafting pleadings."
    >
      <UploadPanel />
    </PageShell>
  );
}
