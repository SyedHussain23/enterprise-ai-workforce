import clsx from 'clsx';

const AGENT_STYLES: Record<string, string> = {
  hr: 'bg-violet-50 text-violet-700',
  it: 'bg-sky-50 text-sky-700',
  finance: 'bg-emerald-50 text-emerald-700',
  guardrail: 'bg-red-50 text-red-700',
  default: 'bg-slate-100 text-slate-600',
};

const AGENT_LABELS: Record<string, string> = {
  hr: 'HR Agent',
  it: 'IT Agent',
  finance: 'Finance Agent',
  guardrail: 'Guardrail',
};

interface Props {
  agent?: string;
}

export function AgentBadge({ agent }: Props) {
  if (!agent) return null;
  const key = agent.toLowerCase().replace('_agent', '');
  const style = AGENT_STYLES[key] ?? AGENT_STYLES.default;
  const label = AGENT_LABELS[key] ?? agent;

  return (
    <span className={clsx('px-2 py-0.5 rounded text-xs font-medium', style)}>{label}</span>
  );
}
