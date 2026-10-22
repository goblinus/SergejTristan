import { ApiError } from './errors';

export type QueryValue = string | number | boolean | null | undefined;

export interface RequestOptions {
  body?: unknown;
  params?: Record<string, QueryValue>;
  signal?: AbortSignal;
}

export interface ResponseResult<T> {
  data: T;
  status: number;
}

const BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '/api').replace(/\/$/, '');
const TIMEOUT_MS = 10_000;

function buildUrl(path: string, params?: Record<string, QueryValue>): string {
  const query = new URLSearchParams();
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null) {
        query.set(key, String(value));
      }
    }
  }
  const qs = query.toString();
  return `${BASE_URL}${path}${qs ? `?${qs}` : ''}`;
}

async function parseBody(response: Response): Promise<unknown> {
  if (response.status === 204) {
    return undefined;
  }
  const text = await response.text();
  if (!text) {
    return undefined;
  }
  return JSON.parse(text) as unknown;
}

/** Выполняет запрос и возвращает тело вместе с HTTP-статусом. */
export async function requestWithStatus<T>(
  method: string,
  path: string,
  options: RequestOptions = {},
): Promise<ResponseResult<T>> {
  const controller = new AbortController();
  let timedOut = false;

  const timer = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, TIMEOUT_MS);

  const external = options.signal;
  const onExternalAbort = (): void => controller.abort();
  if (external) {
    if (external.aborted) {
      controller.abort();
    } else {
      external.addEventListener('abort', onExternalAbort, { once: true });
    }
  }

  const headers: Record<string, string> = { Accept: 'application/json' };
  const hasBody = options.body !== undefined;
  if (hasBody) {
    headers['Content-Type'] = 'application/json';
  }

  const init: RequestInit = {
    method,
    headers,
    signal: controller.signal,
  };
  if (hasBody) {
    init.body = JSON.stringify(options.body);
  }

  let response: Response;
  try {
    response = await fetch(buildUrl(path, options.params), init);
  } catch (error) {
    if (timedOut) {
      throw new ApiError('timeout', 'Сервер не ответил за 10 секунд');
    }
    if (external?.aborted) {
      throw error;
    }
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiError('timeout', 'Запрос отменён');
    }
    throw new ApiError('network', 'Нет соединения с сервером');
  } finally {
    clearTimeout(timer);
    external?.removeEventListener('abort', onExternalAbort);
  }

  if (!response.ok) {
    let body: unknown = null;
    try {
      body = await parseBody(response);
    } catch {
      body = null;
    }
    throw new ApiError('http', `HTTP ${response.status}`, response.status, body);
  }

  try {
    const data = (await parseBody(response)) as T;
    return { data, status: response.status };
  } catch {
    throw new ApiError('parse', 'Не удалось разобрать ответ сервера', response.status);
  }
}

/** Выполняет запрос и возвращает только тело ответа. */
export async function request<T>(
  method: string,
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const result = await requestWithStatus<T>(method, path, options);
  return result.data;
}
