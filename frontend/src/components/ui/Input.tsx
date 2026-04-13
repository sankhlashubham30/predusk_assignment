import { cn } from '@/lib/utils';
import { forwardRef, InputHTMLAttributes } from 'react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, hint, className, ...props }, ref) => (
    <div className="space-y-1.5">
      {label && <label className="block text-xs font-medium text-ink-muted">{label}</label>}
      <input ref={ref}
        className={cn(
          'w-full bg-surface-overlay border rounded-lg px-3 py-2 text-sm text-ink placeholder:text-ink-faint',
          'focus:outline-none focus:border-brand/50 focus:ring-1 focus:ring-brand/20',
          'transition-all duration-150',
          error ? 'border-red-500/50' : 'border-surface-border',
          className
        )} {...props} />
      {error && <p className="text-xs text-red-400">{error}</p>}
      {hint && !error && <p className="text-xs text-ink-faint">{hint}</p>}
    </div>
  )
);
Input.displayName = 'Input';
