export type ApiErrorKind = 'network' | 'timeout' | 'http' | 'parse';

/** Нормализованная ошибка HTTP-слоя. */
export class ApiError extends Error {
  readonly kind: ApiErrorKind;
  readonly status: number | null;
  readonly body: unknown;

  constructor(kind: ApiErrorKind, message: string, status: number | null = null, body: unknown = null) {
    super(message);
    this.name = 'ApiError';
    this.kind = kind;
    this.status = status;
    this.body = body;
  }

  /** Человекочитаемое сообщение: detail из FastAPI или текст ошибки. */
  get detail(): string {
    const body = this.body;
    if (isRecord(body) && 'detail' in body) {
      const detail = body.detail;
      if (typeof detail === 'string') {
        return detail;
      }
      if (Array.isArray(detail) && detail.length > 0) {
        const first = detail[0];
        if (isRecord(first) && typeof first.msg === 'string') {
          return first.msg;
        }
      }
    }
    return this.message;
  }
}

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.detail;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return 'Неизвестная ошибка';
}
