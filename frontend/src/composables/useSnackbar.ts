import { computed, reactive } from 'vue';

export type SnackKind = 'success' | 'error';

export interface SnackAction {
  label: string;
  run: () => void;
}

export interface Snack {
  id: number;
  kind: SnackKind;
  text: string;
  action: SnackAction | null;
}

interface SnackbarState {
  current: Snack | null;
  visible: boolean;
}

const AUTO_CLOSE_MS = 5_000;

const state = reactive<SnackbarState>({
  current: null,
  visible: false,
});

let timer: ReturnType<typeof setTimeout> | null = null;
let nextId = 1;

function clearTimer(): void {
  if (timer !== null) {
    clearTimeout(timer);
    timer = null;
  }
}

function dismiss(): void {
  clearTimer();
  state.visible = false;
  state.current = null;
}

function show(kind: SnackKind, text: string, action: SnackAction | null = null): number {
  clearTimer();
  const id = nextId++;
  state.current = { id, kind, text, action };
  state.visible = true;
  timer = setTimeout(dismiss, AUTO_CLOSE_MS);
  return id;
}

function pause(): void {
  clearTimer();
}

function resume(): void {
  if (state.visible && state.current) {
    clearTimer();
    timer = setTimeout(dismiss, AUTO_CLOSE_MS);
  }
}

function runAction(): void {
  const action = state.current?.action;
  dismiss();
  action?.run();
}

export function useSnackbar() {
  return {
    current: computed(() => state.current),
    visible: computed(() => state.visible),
    success: (text: string, action: SnackAction | null = null) => show('success', text, action),
    error: (text: string, action: SnackAction | null = null) => show('error', text, action),
    dismiss,
    pause,
    resume,
    runAction,
  };
}
