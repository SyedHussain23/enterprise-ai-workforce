/** Status pill — shared by Requests + Approvals UIs. */
import type { ReactNode } from 'react';
import { Clock, CheckCircle, XCircle, Zap, Slash, AlertCircle } from 'lucide-react';
import clsx from 'clsx';

const STYLES: Record<string, { bg: string; text: string; icon: ReactNode; label: string }> = {
  pending:   { bg: 'bg-amber-50 border-amber-200',     text: 'text-amber-700',   icon: <Clock className="w-3 h-3" />,        label: 'Pending' },
  approved:  { bg: 'bg-emerald-50 border-emerald-200', text: 'text-emerald-700', icon: <CheckCircle className="w-3 h-3" />,  label: 'Approved' },
  completed: { bg: 'bg-emerald-50 border-emerald-200', text: 'text-emerald-700', icon: <Zap className="w-3 h-3" />,          label: 'Executed' },
  rejected:  { bg: 'bg-rose-50 border-rose-200',       text: 'text-rose-700',    icon: <XCircle className="w-3 h-3" />,      label: 'Rejected' },
  cancelled: { bg: 'bg-slate-50 border-slate-200',     text: 'text-slate-600',   icon: <Slash className="w-3 h-3" />,        label: 'Cancelled' },
  failed:    { bg: 'bg-orange-50 border-orange-200',   text: 'text-orange-700',  icon: <AlertCircle className="w-3 h-3" />,  label: 'Failed' },
};

export function StatusBadge({ status }: { status: string }) {
  const s = STYLES[status.toLowerCase()] ?? STYLES.pending;
  return (
    <span className={clsx(
      'inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-[10px] font-bold uppercase tracking-wide',
      s.bg, s.text,
    )}>
      {s.icon}
      {s.label}
    </span>
  );
}

const ACTION_LABELS: Record<string, string> = {
  apply_leave:              'Leave Request',
  sick_leave_report:        'Sick Leave Report',
  update_profile:           'Profile Update',
  request_certificate:      'Certificate Request',
  create_ticket:            'IT Support Ticket',
  reset_password:           'Password Reset',
  request_access:           'Access Request',
  submit_expense:           'Expense Claim',
  request_advance:          'Salary Advance',
  query_payslip:            'Payslip Request',
  generate_report:          'Report Request',
  salary_increase_request:  'Salary Increase Request',
  promotion_request:        'Promotion Request',
  transfer_request:         'Internal Transfer',
};

export function actionLabel(t: string): string {
  return ACTION_LABELS[t] ?? t.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}
