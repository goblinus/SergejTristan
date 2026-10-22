<script setup lang="ts">
import type { WatchlistFilter } from '@/types/watchlist';

defineProps<{
  modelValue: WatchlistFilter;
  disabled?: boolean;
}>();

defineEmits<{
  'update:modelValue': [value: WatchlistFilter];
}>();

const OPTIONS: Array<{ value: WatchlistFilter; label: string }> = [
  { value: 'all', label: 'Все' },
  { value: 'hot', label: 'Горячие' },
  { value: 'no_date', label: 'Без даты' },
  { value: 'past', label: 'Прошла' },
];
</script>

<template>
  <div class="filters" role="group" aria-label="Фильтр сторожков">
    <button
      v-for="option in OPTIONS"
      :key="option.value"
      type="button"
      :class="['filter', { 'filter--active': modelValue === option.value }]"
      :disabled="disabled"
      @click="$emit('update:modelValue', option.value)"
    >
      {{ option.label }}
    </button>
  </div>
</template>

<style scoped>
.filters {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.filter {
  border: 1px solid var(--outline);
  border-radius: var(--radius-chip);
  background: transparent;
  color: var(--on-surface-variant);
  padding: 6px 14px;
  font-size: var(--font-size-label-lg);
  line-height: var(--line-height-label-lg);
  font-weight: 500;
}

.filter:hover:not(:disabled) {
  background: color-mix(in srgb, var(--on-surface) 8%, transparent);
  color: var(--on-surface);
}

.filter--active {
  background: var(--primary-container);
  border-color: var(--primary-container);
  color: var(--on-primary-container);
}

.filter:disabled {
  opacity: 0.38;
  cursor: default;
}
</style>
