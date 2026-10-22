import { request, requestWithStatus } from '@/api/http';
import type { Page } from '@/types/page';
import type {
  AddWatchlistResult,
  WatchlistCreate,
  WatchlistItem,
} from '@/types/watchlist';

export function getWatchlist(params: { page?: number; page_size?: number } = {}): Promise<
  Page<WatchlistItem>
> {
  return request<Page<WatchlistItem>>('GET', '/v1/watchlist', { params: { ...params } });
}

export async function addToWatchlist(body: WatchlistCreate): Promise<AddWatchlistResult> {
  const result = await requestWithStatus<WatchlistItem>('POST', '/v1/watchlist', { body });
  return { item: result.data, created: result.status === 201 };
}

export function removeFromWatchlist(ticker: string): Promise<void> {
  return request<void>('DELETE', `/v1/watchlist/${encodeURIComponent(ticker)}`);
}
