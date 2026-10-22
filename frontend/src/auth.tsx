import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import { ApiError, request, type Login, type User, type RequestOptions } from './api';

interface Session { token: string; user: User; expiresAt: number }
interface AuthValue {
  user: User | null; notice: string; warning: string;
  login(email: string, password: string, signal?: AbortSignal): Promise<void>;
  logout(all?: boolean): Promise<void>;
  changePassword(current: string, next: string): Promise<void>;
  refresh(): Promise<void>;
  clearNotice(): void;
  authenticated<T>(path: string, options?: Omit<RequestOptions, 'token'>): Promise<T>;
}
const AuthContext = createContext<AuthValue | null>(null);
export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const current = useRef<Session | null>(null);
  const generation = useRef(0);
  const [notice, setNotice] = useState('');
  const [warning, setWarning] = useState('');
  const clear = useCallback((message: string) => {
    generation.current++; current.current = null; setSession(null); setWarning(''); setNotice(message);
  }, []);
  const refresh = useCallback(async () => {
    const active = current.current;
    if (!active) return;
    if (Date.now() >= active.expiresAt) { clear('Your session has expired. Please sign in again.'); return; }
    try {
      const user = await request<User>('/auth/me', { token: active.token });
      if (current.current !== active) return;
      const updated = { ...active, user }; current.current = updated; setSession(updated); setWarning('');
    } catch (error) {
      if (current.current !== active) return;
      if (error instanceof ApiError && error.status === 401) clear('Your session has ended. Please sign in again.');
      else setWarning('We could not reconnect to your account. Check the local service and retry.');
    }
  }, [clear]);

  const authenticated = useCallback(async <T,>(path: string, options: Omit<RequestOptions, 'token'> = {}): Promise<T> => {
    const active = current.current;
    if (!active || Date.now() >= active.expiresAt) {
      clear('Your session has expired. Please sign in again.');
      throw new ApiError(401, 'SESSION_ENDED');
    }
    try {
      const data = await request<T>(path, { ...options, token: active.token });
      if (current.current?.token !== active.token) throw new DOMException('Session changed', 'AbortError');
      return data;
    } catch (error) {
      if (current.current?.token === active.token && error instanceof ApiError) {
        if (error.status === 401) clear('Your session has ended. Please sign in again.');
        if (error.status === 403) await refresh();
      }
      throw error;
    }
  }, [clear, refresh]);

  useEffect(() => {
    if (!session) return;
    const timer = setTimeout(() => clear('Your session has expired. Please sign in again.'), Math.max(0, session.expiresAt - Date.now()));
    const focus = () => { if (document.visibilityState === 'visible') void refresh(); };
    window.addEventListener('focus', focus); document.addEventListener('visibilitychange', focus);
    return () => { clearTimeout(timer); window.removeEventListener('focus', focus); document.removeEventListener('visibilitychange', focus); };
  }, [session, clear, refresh]);

  const login = async (email: string, password: string, signal?: AbortSignal) => {
    const version = ++generation.current;
    const data = await request<Login>('/auth/login', { body: { email: email.trim(), password }, signal });
    if (version !== generation.current || signal?.aborted) return;
    const next = { token: data.access_token, user: data.user, expiresAt: Date.now() + data.expires_in * 1000 };
    current.current = next; setSession(next); setNotice(''); setWarning('');
  };
  const logout = async (all = false) => {
    const active = current.current;
    if (!active) return;
    try {
      await request<void>(all ? '/auth/logout-all' : '/auth/logout', { token: active.token, method: 'POST' });
      if (current.current?.token === active.token) clear(all ? 'All sessions have been signed out.' : 'You have been signed out.');
    } catch (error) {
      if (current.current?.token !== active.token) return;
      if (error instanceof ApiError && error.status === 401) clear('Your session has ended. Please sign in again.');
      else throw error; // Keep the session so revocation can be retried; never report false success.
    }
  };
  const changePassword = async (oldPassword: string, newPassword: string) => {
    const active = current.current;
    if (!active) return;
    try {
      await request<void>('/auth/change-password', { token: active.token, body: { current_password: oldPassword, new_password: newPassword } });
      if (current.current?.token === active.token) clear('Password updated. All sessions have ended. Sign in with your new password.');
    } catch (error) {
      if (current.current?.token !== active.token) return;
      if (error instanceof ApiError && error.status === 401) await refresh();
      throw error;
    }
  };
  return <AuthContext.Provider value={{ user: session?.user ?? null, notice, warning, login, logout, changePassword, refresh, authenticated, clearNotice: () => setNotice('') }}>{children}</AuthContext.Provider>;
}
export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error('AuthProvider is required');
  return value;
}
