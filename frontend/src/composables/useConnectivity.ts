import { computed, reactive } from 'vue';

import { ApiError } from '@/api/errors';

interface ConnectivityState {
  browserOnline: boolean;
  networkFailed: boolean;
}

const state = reactive<ConnectivityState>({
  browserOnline: typeof navigator === 'undefined' ? true : navigator.onLine,
  networkFailed: false,
});

let listening = false;

function ensureListeners(): void {
  if (listening || typeof window === 'undefined') {
    return;
  }
  listening = true;
  window.addEventListener('online', () => {
    state.browserOnline = true;
    state.networkFailed = false;
  });
  window.addEventListener('offline', () => {
    state.browserOnline = false;
  });
}

/** Глобальное офлайн-состояние: сеть браузера + ошибки kind='network'. */
export function useConnectivity() {
  ensureListeners();

  return {
    isOffline: computed(() => !state.browserOnline || state.networkFailed),
    browserOnline: computed(() => state.browserOnline),
    reportError: (error: unknown): void => {
      if (error instanceof ApiError && (error.kind === 'network' || error.kind === 'timeout')) {
        state.networkFailed = true;
      }
    },
    reportSuccess: (): void => {
      state.networkFailed = false;
    },
  };
}
