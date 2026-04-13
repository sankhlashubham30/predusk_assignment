'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LayoutDashboard, Upload, LogOut, FileStack, Activity } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuthStore } from '@/store/authStore';
import { useRouter } from 'next/navigation';

const nav = [
  { href: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { href: '/upload', icon: Upload, label: 'Upload' },
];

export function Sidebar() {
  const pathname = usePathname();
  const { logout, user } = useAuthStore();
  const router = useRouter();

  const handleLogout = () => { logout(); router.push('/login'); };

  return (
    <aside className="fixed left-0 top-0 h-full w-56 bg-surface-raised border-r border-surface-border flex flex-col z-40">
      {/* Logo */}
      <div className="p-5 border-b border-surface-border">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-brand/20 border border-brand/30 flex items-center justify-center">
            <FileStack className="w-4 h-4 text-brand" />
          </div>
          <span className="font-semibold text-ink text-sm tracking-tight">DocFlow</span>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 p-3 space-y-0.5">
        {nav.map(({ href, icon: Icon, label }) => (
          <Link key={href} href={href}
            className={cn(
              'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all duration-150',
              pathname === href || pathname.startsWith(href + '/')
                ? 'bg-brand/10 text-brand border border-brand/20'
                : 'text-ink-muted hover:text-ink hover:bg-surface-hover'
            )}>
            <Icon className="w-4 h-4 flex-shrink-0" />
            {label}
          </Link>
        ))}
      </nav>

      {/* User */}
      <div className="p-3 border-t border-surface-border">
        <div className="flex items-center gap-3 px-3 py-2 rounded-lg">
          <div className="w-6 h-6 rounded-full bg-brand/20 border border-brand/30 flex items-center justify-center flex-shrink-0">
            <span className="text-brand text-xs font-medium">
              {user?.username?.[0]?.toUpperCase() || 'U'}
            </span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-ink truncate">{user?.username || 'User'}</p>
            <p className="text-xs text-ink-faint truncate">{user?.email || ''}</p>
          </div>
        </div>
        <button onClick={handleLogout}
          className="w-full mt-1 flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-ink-muted hover:text-red-400 hover:bg-red-400/5 transition-all duration-150">
          <LogOut className="w-4 h-4" />
          Sign out
        </button>
      </div>
    </aside>
  );
}
