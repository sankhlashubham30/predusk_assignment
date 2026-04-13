'use client';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Sidebar } from '@/components/layout/Sidebar';
import { useAuthStore } from '@/store/authStore';

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { hydrate, isAuthenticated } = useAuthStore();
  const router = useRouter();

  useEffect(() => {
    hydrate();
    const token = localStorage.getItem('docflow_token');
    if (!token) router.push('/login');
  }, []);

  return (
    <div className="flex h-screen bg-[#0a0a0b] overflow-hidden">
      <Sidebar />
      <main className="flex-1 ml-56 overflow-auto">
        {children}
      </main>
    </div>
  );
}
