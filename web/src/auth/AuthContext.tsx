/**
 * 全局登录态：token + user 存 localStorage，供所有视图读取。
 */
import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { me, type AuthUser } from '../api/auth';

interface AuthState {
  user: AuthUser | null;
  ready: boolean; // 是否完成启动时的会话恢复
  login: (token: string, user: AuthUser) => void;
  updateUser: (user: AuthUser) => void;
  logout: () => void;
}

const Ctx = createContext<AuthState>({
  user: null,
  ready: false,
  login: () => {},
  updateUser: () => {},
  logout: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('lwm_token');
    if (!token) {
      setReady(true);
      return;
    }
    me()
      .then((res) => setUser(res.user))
      .catch(() => localStorage.removeItem('lwm_token'))
      .finally(() => setReady(true));
  }, []);

  const login = useCallback((token: string, u: AuthUser) => {
    localStorage.setItem('lwm_token', token);
    setUser(u);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('lwm_token');
    setUser(null);
  }, []);

  return (
    <Ctx.Provider value={{ user, ready, login, updateUser: setUser, logout }}>
      {children}
    </Ctx.Provider>
  );
}

export function useAuth() {
  return useContext(Ctx);
}
