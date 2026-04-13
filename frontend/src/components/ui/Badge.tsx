import { cn, getStatusColor, getStatusDot } from '@/lib/utils';
import { JobStatus } from '@/types';

export function StatusBadge({ status }: { status: JobStatus }) {
  return (
    <span className={cn('inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium border', getStatusColor(status))}>
      <span className={cn('w-1.5 h-1.5 rounded-full flex-shrink-0', getStatusDot(status))} />
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}

export function Badge({ children, variant = 'default', className }: {
  children: React.ReactNode;
  variant?: 'default' | 'outline' | 'success' | 'warning';
  className?: string;
}) {
  return (
    <span className={cn(
      'inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium border',
      variant === 'default' && 'bg-surface-overlay text-ink-muted border-surface-border',
      variant === 'outline' && 'bg-transparent text-ink-muted border-surface-border',
      variant === 'success' && 'bg-emerald-400/10 text-emerald-400 border-emerald-400/20',
      variant === 'warning' && 'bg-amber-400/10 text-amber-400 border-amber-400/20',
      className
    )}>
      {children}
    </span>
  );
}
