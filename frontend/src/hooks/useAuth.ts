import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';

export function useAuth(requireAuth = true) {
  const { isAuthenticated, user, token, hydrate } = useAuthStore();
  const router = useRouter();

  useEffect(() => {
    hydrate();
  }, []);

  useEffect(() => {
    if (requireAuth && !isAuthenticated && !localStorage.getItem('docflow_token')) {
      router.push('/login');
    }
  }, [isAuthenticated, requireAuth]);

  return { isAuthenticated, user, token };
}
