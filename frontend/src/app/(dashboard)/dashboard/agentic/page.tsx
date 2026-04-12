import { EmptyState } from "@/components/shared/EmptyState";

export default function AgenticPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">AI Ready</h1>
      <EmptyState
        title="Coming in Phase 5"
        message="Agentic readiness and compliance views will ship in the next phase."
      />
    </div>
  );
}
