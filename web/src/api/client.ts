/**
 * 统一请求客户端。
 *
 * 职责：
 *  1. 统一解包网关响应 { ok, data, error }；
 *  2. 超时控制（默认 10s，分析类端点可放宽）；
 *  3. mock 兜底开关（VITE_LWM_USE_MOCK=1 时调用方走 mocks，不发请求）；
 *  4. 后端不可用降级：记录 degraded 状态，页面顶部展示横幅而非白屏。
 */
import { API_BASE } from './endpoints';

export const USE_MOCK = import.meta.env.VITE_LWM_USE_MOCK === '1';

export interface ApiErrorBody {
  code: string;
  message: string;
  detail?: unknown;
}

export class LwmApiError extends Error {
  readonly code: string;
  readonly detail?: unknown;
  readonly status: number;

  constructor(status: number, body: ApiErrorBody) {
    super(body.message);
    this.name = 'LwmApiError';
    this.code = body.code;
    this.detail = body.detail;
    this.status = status;
  }
}

// --- 降级状态（后端不可用广播） ---
let degraded = false;
const listeners = new Set<(v: boolean) => void>();

export function isDegraded() {
  return degraded;
}

export function subscribeDegraded(fn: (v: boolean) => void) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

function setDegraded(v: boolean) {
  if (degraded === v) return;
  degraded = v;
  listeners.forEach((fn) => fn(v));
}

export async function request<T>(
  path: string,
  init: RequestInit & { timeoutMs?: number } = {},
): Promise<T> {
  const { timeoutMs = 10_000, ...rest } = init;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(`${API_BASE}${path}`, {
      ...rest,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...(rest.headers ?? {}),
      },
    });

    const text = await res.text();
    let payload: unknown;
    try {
      payload = text ? JSON.parse(text) : null;
    } catch {
      // 网关异常时可能返回纯文本（如 http.server 默认错误页）
      setDegraded(true);
      throw new LwmApiError(res.status, {
        code: 'E_BAD_JSON',
        message: `网关返回非 JSON 响应（HTTP ${res.status}）`,
        detail: text.slice(0, 200),
      });
    }

    const body = payload as { ok?: boolean; data?: T; error?: ApiErrorBody } | null;
    if (!res.ok || body?.ok === false) {
      // 4xx/5xx 中只有网络不可达类（0/5xx）才触发全局降级
      if (res.status >= 500 || res.status === 0) setDegraded(true);
      throw new LwmApiError(res.status, body?.error ?? { code: 'E_UNKNOWN', message: res.statusText });
    }

    setDegraded(false);
    return (body?.data ?? payload) as T;
  } catch (err) {
    if (err instanceof LwmApiError) throw err;
    // fetch 网络层失败（网关未启动 / 被 CORS 拦截 / 超时）
    setDegraded(true);
    const aborted = (err as Error)?.name === 'AbortError';
    throw new LwmApiError(0, {
      code: aborted ? 'E_TIMEOUT' : 'E_NETWORK',
      message: aborted ? `请求超时（${timeoutMs}ms）：${path}` : `无法连接网关：${path}`,
    });
  } finally {
    clearTimeout(timer);
  }
}

/** 带 query 参数的 GET 构造 */
export function withQuery(path: string, params: Record<string, string | number | undefined>): string {
  const usp = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== '') usp.set(k, String(v));
  });
  const qs = usp.toString();
  return qs ? `${path}?${qs}` : path;
}
