import React from "react";
import { AlertCircle, CheckCircle2, Info, AlertTriangle, X } from "lucide-react";

export interface AlertProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "info" | "warning" | "danger" | "success";
  title?: string;
  onClose?: () => void;
}

const variantStyles = {
  info: {
    container: "bg-civic-50 text-civic-900 border-civic-200",
    icon: <Info className="w-5 h-5 text-civic-600 shrink-0 mt-0.5" aria-hidden="true" />,
  },
  warning: {
    container: "bg-amber-50 text-amber-900 border-amber-200",
    icon: <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" aria-hidden="true" />,
  },
  danger: {
    container: "bg-rose-50 text-rose-900 border-rose-200",
    icon: <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" aria-hidden="true" />,
  },
  success: {
    container: "bg-emerald-50 text-emerald-900 border-emerald-200",
    icon: <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" aria-hidden="true" />,
  },
};

export const Alert: React.FC<AlertProps> = ({
  children,
  variant = "info",
  title,
  onClose,
  className = "",
  ...props
}) => {
  const current = variantStyles[variant];

  return (
    <div
      role="alert"
      className={`rounded-lg border p-4 flex gap-3 text-sm transition-all ${current.container} ${className}`}
      {...props}
    >
      {current.icon}
      <div className="flex-1">
        {title && <h4 className="font-semibold text-base mb-1">{title}</h4>}
        <div className="leading-relaxed">{children}</div>
      </div>
      {onClose && (
        <button
          onClick={onClose}
          type="button"
          aria-label="Dismiss alert"
          className="text-slate-500 hover:text-slate-800 p-1 -mr-1 -mt-1 rounded focus:outline-none focus:ring-2 focus:ring-offset-1"
        >
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  );
};
