<script setup lang="ts">
import { computed } from 'vue';

import { formatDsi } from '@/utils/formatDividend';

import { DSI_HINT } from './dsiHint';

const props = defineProps<{
  value: number | null;
}>();

const display = computed(() => formatDsi(props.value));
</script>

<template>
  <span class="dsi">
    <span class="dsi__label">DSI</span>
    <span class="dsi__value tabular">{{ display }}</span>
    <button
      type="button"
      class="dsi__hint"
      :aria-label="DSI_HINT"
      @click.stop
      @keydown.stop
      @pointerdown.stop
    >
      <span aria-hidden="true">i</span>
      <span class="dsi__tooltip" aria-hidden="true">{{ DSI_HINT }}</span>
    </button>
  </span>
</template>

<style scoped>
.dsi {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  position: relative;
  font-size: var(--font-size-label-md);
  line-height: var(--line-height-label-md);
}

.dsi__label {
  color: var(--on-surface-muted);
}

.dsi__value {
  color: var(--on-surface);
  font-weight: 600;
  font-feature-settings: 'tnum';
}

.dsi__hint {
  position: relative;
  width: 16px;
  height: 16px;
  padding: 0;
  border: 1px solid var(--outline);
  border-radius: 50%;
  background: transparent;
  color: var(--on-surface-muted);
  font-size: 11px;
  line-height: 1;
  font-weight: 600;
  display: grid;
  place-items: center;
}

.dsi__hint:hover,
.dsi__hint:focus-visible {
  color: var(--on-surface);
  border-color: var(--on-surface-variant);
}

.dsi__tooltip {
  position: absolute;
  bottom: calc(100% + 8px);
  right: 0;
  width: 250px;
  padding: 10px 12px;
  border-radius: 8px;
  background: var(--surface-4);
  border: 1px solid var(--outline);
  box-shadow: var(--shadow-modal);
  color: var(--on-surface);
  font-size: 12px;
  line-height: 16px;
  font-weight: 400;
  text-align: left;
  white-space: normal;
  pointer-events: none;
  opacity: 0;
  transform: translateY(4px);
  transition:
    opacity 0.15s ease,
    transform 0.15s ease;
  z-index: var(--z-modal);
}

.dsi__hint:hover .dsi__tooltip,
.dsi__hint:focus-visible .dsi__tooltip {
  opacity: 1;
  transform: translateY(0);
}
</style>
