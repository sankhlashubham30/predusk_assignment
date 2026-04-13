import { cn } from '@/lib/utils';

export function ProgressBar({ value, className, animated }: {
  value: number;
  className?: string;
  animated?: boolean;
}) {
  return (
    <div className={cn('w-full h-1 bg-surface-border rounded-full overflow-hidden', className)}>
      <div
        className={cn('h-full rounded-full transition-all duration-500 ease-out',
          value >= 100 ? 'bg-emerald-400' : 'bg-brand',
          animated && value < 100 && 'relative overflow-hidden'
        )}
        style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
      >
        {animated && value > 0 && value < 100 && (
          <span className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent progress-indeterminate" />
        )}
      </div>
    </div>
  );
}
