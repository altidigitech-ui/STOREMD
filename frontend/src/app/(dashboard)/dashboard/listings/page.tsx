import { EmptyState } from "@/components/shared/EmptyState";

export default function ListingsPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Listings</h1>
      <EmptyState
        title="Coming in Phase 5"
        message="Listings scanner is ready on the backend. The dashboard view will ship in the next phase."
      />
    </div>
  );
}
