import { computed, reactive } from 'vue';

import { addToWatchlist, getWatchlist, removeFromWatchlist } from '@/api/endpoints/watchlist';
import { ApiError } from '@/api/errors';
import type { WatchlistItem } from '@/types/watchlist';

import { useConnectivity } from './useConnectivity';
import { useSnackbar } from './useSnackbar';

interface WatchlistState {
  items: WatchlistItem[] | null;
  isLoading: boolean;
  error: ApiError | null;
}

interface RemovedSnapshot {
  ticker: string;
  threshold_days: number;
}

const state = reactive<WatchlistState>({
  items: null,
  isLoading: false,
  error: null,
});

const mutating = reactive(new Set<string>());
let lastRemoved: RemovedSnapshot | null = null;

const HOT_STATUSES = new Set(['hot', 'critical']);

function statusRank(item: WatchlistItem): number {
  if (item.next_record_date !== null) {
    return 0;
  }
  return item.status === 'past' ? 2 : 1;
}

/** Канонический серверный порядок (Р-7): датированные → no_date → past. */
function compareItems(a: WatchlistItem, b: WatchlistItem): number {
  const rankDiff = statusRank(a) - statusRank(b);
  if (rankDiff !== 0) {
    return rankDiff;
  }
  if (a.next_record_date !== null && b.next_record_date !== null) {
    const dateDiff = a.next_record_date.localeCompare(b.next_record_date);
    if (dateDiff !== 0) {
      return dateDiff;
    }
  }
  return a.ticker.localeCompare(b.ticker);
}

function upsert(item: WatchlistItem): void {
  const items = state.items ?? [];
  const index = items.findIndex((entry) => entry.ticker === item.ticker);
  if (index >= 0) {
    items[index] = item;
  } else {
    items.push(item);
  }
  items.sort(compareItems);
  state.items = [...items];
}

function drop(ticker: string): void {
  if (!state.items) {
    return;
  }
  state.items = state.items.filter((entry) => entry.ticker !== ticker);
}

async function reload(): Promise<void> {
  if (state.isLoading) {
    return;
  }
  const snackbar = useSnackbar();
  const connectivity = useConnectivity();
  state.isLoading = true;
  state.error = null;
  try {
    const page = await getWatchlist({ page: 1, page_size: 100 });
    state.items = [...page.items].sort(compareItems);
    connectivity.reportSuccess();
  } catch (error) {
    const apiError = error instanceof ApiError ? error : new ApiError('network', 'Ошибка загрузки');
    state.error = apiError;
    connectivity.reportError(apiError);
    if (apiError.kind === 'network') {
      snackbar.error('Нет соединения. Данные могли устареть.');
    }
  } finally {
    state.isLoading = false;
  }
}

async function mutateAdd(
  ticker: string,
  thresholdDays: number | undefined,
  silent: boolean,
): Promise<boolean> {
  const snackbar = useSnackbar();
  const connectivity = useConnectivity();
  if (mutating.has(ticker)) {
    return false;
  }
  mutating.add(ticker);
  try {
    const body =
      thresholdDays === undefined ? { ticker } : { ticker, threshold_days: thresholdDays };
    const result = await addToWatchlist(body);
    upsert(result.item);
    connectivity.reportSuccess();
    if (!silent) {
      snackbar.success(result.created ? 'Сторожок установлен' : 'Уже отслеживается');
    }
    return true;
  } catch (error) {
    const apiError = error instanceof ApiError ? error : new ApiError('network', 'Ошибка запроса');
    connectivity.reportError(apiError);
    const retry = apiError.status === 404 ? null : { label: 'Повторить', run: () => void add(ticker) };
    snackbar.error(`Не удалось добавить ${ticker}.`, retry);
    return false;
  } finally {
    mutating.delete(ticker);
  }
}

async function add(ticker: string): Promise<boolean> {
  return mutateAdd(ticker, undefined, false);
}

async function remove(ticker: string): Promise<void> {
  const snackbar = useSnackbar();
  const connectivity = useConnectivity();
  if (mutating.has(ticker)) {
    return;
  }
  const item = state.items?.find((entry) => entry.ticker === ticker);
  const snapshot: RemovedSnapshot | null = item
    ? { ticker: item.ticker, threshold_days: item.threshold_days }
    : null;

  mutating.add(ticker);
  try {
    await removeFromWatchlist(ticker);
    drop(ticker);
    connectivity.reportSuccess();
    lastRemoved = snapshot;
    const undo = snapshot
      ? { label: 'Отменить', run: () => void undoRemove() }
      : null;
    snackbar.success('Сторожок снят', undo);
  } catch (error) {
    const apiError = error instanceof ApiError ? error : new ApiError('network', 'Ошибка запроса');
    connectivity.reportError(apiError);
    snackbar.error(`Не удалось снять ${ticker}.`, {
      label: 'Повторить',
      run: () => void remove(ticker),
    });
  } finally {
    mutating.delete(ticker);
  }
}

async function undoRemove(): Promise<void> {
  const snapshot = lastRemoved;
  if (!snapshot) {
    return;
  }
  lastRemoved = null;
  const restored = await mutateAdd(snapshot.ticker, snapshot.threshold_days, true);
  if (restored) {
    useSnackbar().success('Восстановлено');
  }
}

export function useWatchlist() {
  return {
    items: computed(() => state.items),
    isLoading: computed(() => state.isLoading),
    error: computed(() => state.error),
    errorText: computed(() => state.error?.detail ?? null),
    reload,
    add,
    remove,
    undoRemove,
    isMutating: (ticker: string) => mutating.has(ticker),
    isWatched: (ticker: string) =>
      state.items?.some((item) => item.ticker === ticker) ?? false,
    itemFor: (ticker: string): WatchlistItem | null =>
      state.items?.find((item) => item.ticker === ticker) ?? null,
    watchedTickers: computed(
      () => new Set((state.items ?? []).map((item) => item.ticker)),
    ),
    hotCount: computed(
      () => state.items?.filter((item) => HOT_STATUSES.has(item.status)).length ?? 0,
    ),
    hasLoaded: computed(() => state.items !== null),
  };
}
