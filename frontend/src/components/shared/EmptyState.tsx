import type { ReactNode } from "react";

interface EmptyStateProps {
  title?: string;
  message: string;
  action?: ReactNode;
}

export function EmptyState({ title, message, action }: EmptyStateProps) {
  return (
    <div className="rounded-lg border border-dashed border-gray-300 bg-white p-8 text-center">
      {title && (
        <h3 className="text-base font-medium text-gray-900">{title}</h3>
      )}
      <p className="mt-1 text-sm text-gray-500">{message}</p>
      {action && <div className="mt-4 flex justify-center">{action}</div>}
    </div>
  );
}
