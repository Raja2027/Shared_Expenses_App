import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { loginUser, registerUser, fetchMe } from '../api/auth';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(() => localStorage.getItem('shared_expenses_token') || '');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }
    fetchMe()
      .then((data) => {
        setUser(data);
      })
      .catch(() => {
        setToken('');
        setUser(null);
        localStorage.removeItem('shared_expenses_token');
      })
      .finally(() => setLoading(false));
  }, [token]);

  const login = useCallback(async (email, password) => {
    const payload = await loginUser(email, password);
    setToken(payload.access_token);
    setUser(payload.user);
    localStorage.setItem('shared_expenses_token', payload.access_token);
    return payload.user;
  }, []);

  const register = useCallback(async (name, email, password) => {
    await registerUser(name, email, password);
    return login(email, password);
  }, [login]);

  const logout = useCallback(() => {
    setToken('');
    setUser(null);
    localStorage.removeItem('shared_expenses_token');
  }, []);

  return (
    <AuthContext.Provider value={{ user, token, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
