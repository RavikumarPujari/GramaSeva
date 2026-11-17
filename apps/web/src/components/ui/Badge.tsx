import React from "react";

export type StatusType =
  | "DRAFT"
  | "SUBMITTED"
  | "UNDER_REVIEW"
  | "ASSIGNED"
  | "IN_PROGRESS"
  | "REPAIR_REPORTED"
  | "RESOLUTION_REVIEW"
  | "RESOLVED"
  | "NEEDS_INFORMATION"
  | "REOPENED"
  | "REJECTED";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  status?: StatusType;
  variant?: "neutral" | "info" | "warning" | "success" | "danger";
  size?: "sm" | "md";
}

const statusStyles: Record<StatusType, string> = {
  DRAFT: "bg-slate-100 text-slate-700 border-slate-300",
  SUBMITTED: "bg-sky-50 text-sky-700 border-sky-300",
  UNDER_REVIEW: "bg-amber-50 text-amber-800 border-amber-300",
  ASSIGNED: "bg-indigo-50 text-indigo-700 border-indigo-300",
  IN_PROGRESS: "bg-blue-50 text-blue-700 border-blue-300",
  REPAIR_REPORTED: "bg-orange-50 text-orange-800 border-orange-300 font-semibold",
  RESOLUTION_REVIEW: "bg-purple-50 text-purple-700 border-purple-300",
  RESOLVED: "bg-emerald-50 text-emerald-800 border-emerald-300 font-semibold",
  NEEDS_INFORMATION: "bg-yellow-50 text-yellow-800 border-yellow-300",
  REOPENED: "bg-rose-50 text-rose-800 border-rose-300 font-semibold",
  REJECTED: "bg-slate-200 text-slate-700 border-slate-400",
};

const variantStyles = {
  neutral: "bg-slate-100 text-slate-700 border-slate-300",
  info: "bg-blue-50 text-blue-700 border-blue-300",
  warning: "bg-amber-50 text-amber-800 border-amber-300",
  success: "bg-emerald-50 text-emerald-800 border-emerald-300",
  danger: "bg-rose-50 text-rose-800 border-rose-300",
};

export const Badge: React.FC<BadgeProps> = ({
  children,
  status,
  variant,
  size = "md",
  className = "",
  ...props
}) => {
  const chosenStyle = status
    ? statusStyles[status]
    : variant
    ? variantStyles[variant]
    : variantStyles.neutral;

  const sizeStyle = size === "sm" ? "text-xs px-2 py-0.5" : "text-sm px-2.5 py-1";

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-medium rounded-full border ${chosenStyle} ${sizeStyle} ${className}`}
      {...props}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-current opacity-70" aria-hidden="true" />
      {children}
    </span>
  );
};
