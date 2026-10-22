import { request } from '@/api/http';
import type { Page } from '@/types/page';
import type { Ticker, TickersQuery } from '@/types/ticker';

export function getTickers(params: TickersQuery = {}, signal?: AbortSignal): Promise<Page<Ticker>> {
  return request<Page<Ticker>>('GET', '/v1/tickers', {
    params: { ...params },
    ...(signal ? { signal } : {}),
  });
}
