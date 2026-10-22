<script setup lang="ts">
withDefaults(
  defineProps<{
    ticker: string;
    watched?: boolean;
    past?: boolean;
  }>(),
  { watched: false, past: false },
);
</script>

<template>
  <span :class="['ticker-chip', { 'ticker-chip--watched': watched, 'ticker-chip--past': past }]">
    <span class="ticker-chip__label">{{ ticker }}</span>
    <span v-if="watched" class="ticker-chip__dot" aria-hidden="true" />
  </span>
</template>

<style scoped>
.ticker-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 2px 8px;
  border-radius: var(--radius-chip);
  background: var(--surface-3);
  color: var(--on-surface);
  font-size: var(--font-size-label-lg);
  line-height: var(--line-height-label-lg);
  font-weight: 600;
  letter-spacing: 0.02em;
}

.ticker-chip--watched {
  background: var(--primary-container);
  color: var(--on-primary-container);
}

.ticker-chip--past {
  color: var(--past);
}

.ticker-chip__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--primary);
}
</style>
