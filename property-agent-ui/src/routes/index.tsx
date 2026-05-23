import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/AppShell";
import { DevPanel } from "@/components/DevPanel";
import { StateChip } from "@/components/StateChip";
import { PhaseOneForm } from "@/components/phases/PhaseOneForm";
import { SemanticAligning } from "@/components/phases/SemanticAligning";
import { ProfilingComplete } from "@/components/phases/ProfilingComplete";
import { Conversation } from "@/components/phases/Conversation";
import { Searching } from "@/components/phases/Searching";
import { ResultsBatch } from "@/components/phases/ResultsBatch";
import { ActionRequired } from "@/components/phases/ActionRequired";
import { Tier3NoResult } from "@/components/phases/Tier3NoResult";
import { useAppStore } from "@/lib/store";

export const Route = createFileRoute("/")({
  component: Index,
});

function Index() {
  const appState = useAppStore((s) => s.appState);

  return (
    <AppShell>
      {appState !== "IDLE" && (
        <div className="mb-6">
          <StateChip state={appState} />
        </div>
      )}
      <SwitchView />
      <DevPanel />
    </AppShell>
  );
}

function SwitchView() {
  const appState = useAppStore((s) => s.appState);
  switch (appState) {
    case "IDLE":
      return <PhaseOneForm />;
    case "SEMANTIC_ALIGNING":
      return <SemanticAligning />;
    case "PROFILING_COMPLETE":
      return <ProfilingComplete />;
    case "CHATTING":
    case "PENDING_CONFIRMATION":
      return <Conversation />;
    case "SEARCHING":
      return <Searching />;
    case "BATCH_1_DISPLAY":
    case "BATCH_2_DISPLAY":
    case "ALL_REJECTED":
      return <ResultsBatch />;
    case "ACTION_REQUIRED_UI":
      return <ActionRequired />;
    case "TIER3_NO_RESULT":
      return <Tier3NoResult />;
    default:
      return <PhaseOneForm />;
  }
}
