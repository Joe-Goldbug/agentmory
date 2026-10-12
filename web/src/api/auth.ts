/**
 * 认证 API：邮箱注册/登录 + Solana 钱包登录。
 * 后端：lwm/webauth.py（网关 /api/auth/*）。
 */
import { request } from './client';

export interface AuthUser {
  email: string;
  name: string;
  wallets: string[];
}

export interface AuthResult {
  token: string;
  user: AuthUser;
}

export function register(email: string, password: string, name?: string) {
  return request<AuthResult>('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, password, name }),
  });
}

export function login(email: string, password: string) {
  return request<AuthResult>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}

export function walletNonce(address: string) {
  return request<{ nonce: string }>('/api/auth/wallet/nonce', {
    method: 'POST',
    body: JSON.stringify({ address }),
  });
}

export function walletVerify(address: string, nonce: string, signature: string, email?: string) {
  return request<AuthResult>('/api/auth/wallet/verify', {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ address, nonce, signature, email }),
  });
}

export function me() {
  return request<{ user: AuthUser }>('/api/auth/me', {
    headers: authHeaders(),
  });
}

export function logout() {
  return request<{ ok: boolean }>('/api/auth/logout', {
    method: 'POST',
    headers: authHeaders(),
  });
}

export function authHeaders(): Record<string, string> {
  const token = localStorage.getItem('lwm_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}
