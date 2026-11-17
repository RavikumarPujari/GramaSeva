import React from "react";
import { Loader2 } from "lucide-react";

export interface LoadingStateProps {
  message?: string;
  className?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  message = "Loading details...",
  className = "",
}) => {
  return (
    <div
      role="status"
      aria-live="polite"
      className={`flex flex-col items-center justify-center p-8 space-y-3 text-slate-500 ${className}`}
    >
      <Loader2 className="w-8 h-8 animate-spin text-civic-600" aria-hidden="true" />
      <p className="text-sm font-medium">{message}</p>
    </div>
  );
};
