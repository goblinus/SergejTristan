import { computed, onBeforeUnmount, ref, watch, type Ref } from 'vue';

import { getTickers } from '@/api/endpoints/tickers';
import { ApiError } from '@/api/errors';
import type { Ticker } from '@/types/ticker';

const DEBOUNCE_MS = 300;
const MIN_QUERY_LENGTH = 2;

/** Поиск тикеров с debounce 300 мс и отменой предыдущего запроса. */
export function useTickersSearch(query: Ref<string>) {
  const results = ref<Ticker[]>([]);
  const isLoading = ref(false);
  const error = ref<ApiError | null>(null);

  let timer: ReturnType<typeof setTimeout> | null = null;
  let controller: AbortController | null = null;

  function cancelTimer(): void {
    if (timer !== null) {
      clearTimeout(timer);
      timer = null;
    }
  }

  function cancelRequest(): void {
    controller?.abort();
    controller = null;
  }

  async function run(term: string): Promise<void> {
    cancelRequest();
    const current = new AbortController();
    controller = current;
    isLoading.value = true;
    error.value = null;
    try {
      const page = await getTickers({ q: term, page: 1, page_size: 20 }, current.signal);
      if (controller === current) {
        results.value = page.items;
      }
    } catch (caught) {
      if (current.signal.aborted) {
        return;
      }
      error.value =
        caught instanceof ApiError ? caught : new ApiError('network', 'Ошибка поиска');
      results.value = [];
    } finally {
      if (controller === current) {
        isLoading.value = false;
      }
    }
  }

  watch(
    query,
    (value) => {
      cancelTimer();
      const term = value.trim();
      if (term.length < MIN_QUERY_LENGTH) {
        cancelRequest();
        results.value = [];
        error.value = null;
        isLoading.value = false;
        return;
      }
      timer = setTimeout(() => {
        void run(term);
      }, DEBOUNCE_MS);
    },
    { immediate: true },
  );

  onBeforeUnmount(() => {
    cancelTimer();
    cancelRequest();
  });

  return {
    results,
    isLoading,
    error,
    errorText: computed(() => error.value?.detail ?? null),
    minQueryLength: MIN_QUERY_LENGTH,
  };
}
