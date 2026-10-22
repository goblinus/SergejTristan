<script setup lang="ts">
import { useRoute } from 'vue-router';

import AppIcon from '@/components/ui/AppIcon.vue';

withDefaults(
  defineProps<{
    freshness: string | null;
    isLoading?: boolean;
    hotCount?: number;
    showWatchlistTabs?: boolean;
    hasWatchlistLoaded?: boolean;
  }>(),
  {
    isLoading: false,
    hotCount: 0,
    showWatchlistTabs: true,
    hasWatchlistLoaded: false,
  },
);

defineEmits<{
  refresh: [];
}>();

const route = useRoute();
</script>

<template>
  <header class="appbar">
    <div class="appbar__inner">
      <div class="brand">
        <span class="brand__mark" aria-hidden="true">◇</span>
        <span class="brand__text">Дивидендный календарь</span>
      </div>

      <nav v-if="showWatchlistTabs" class="tabs" aria-label="Основная навигация">
        <RouterLink
          :to="{ name: 'calendar' }"
          :class="['tab', { 'tab--active': route.name === 'calendar' }]"
        >
          Календарь
        </RouterLink>
        <RouterLink :to="{ name: 'me' }" :class="['tab', { 'tab--active': route.name === 'me' }]">
          Мои сторожки
          <span
            v-if="(hotCount ?? 0) > 0 && hasWatchlistLoaded"
            class="badge tabular"
            aria-label="Горячих сторожков"
          >
            {{ hotCount ?? 0 }}
          </span>
        </RouterLink>
      </nav>

      <div class="appbar__actions">
        <span v-if="freshness" class="appbar__freshness">{{ freshness }}</span>
        <button
          class="refresh"
          type="button"
          :disabled="isLoading"
          aria-label="Обновить данные"
          title="Обновить данные"
          @click="$emit('refresh')"
        >
          <AppIcon name="refresh" :size="24" :class="{ 'refresh--spinning': isLoading }" />
        </button>
      </div>
    </div>
    <div v-if="isLoading" class="progress" aria-hidden="true" />
  </header>
</template>

<style scoped>
.appbar {
  position: sticky;
  top: 0;
  z-index: var(--z-header);
  background: var(--surface-1);
  border-bottom: 1px solid var(--outline-variant);
}

.appbar__inner {
  max-width: var(--content-max);
  margin: 0 auto;
  min-height: 64px;
  padding: 8px var(--space-6);
  display: flex;
  align-items: center;
  gap: var(--space-6);
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  white-space: nowrap;
}

.brand__mark {
  color: var(--primary);
  font-size: 20px;
  line-height: 1;
}

.brand__text {
  font-size: var(--font-size-title-lg);
  line-height: var(--line-height-title-lg);
  font-weight: 600;
  letter-spacing: -0.01em;
}

.tabs {
  display: flex;
  gap: var(--space-1);
}

.tab {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: 8px 14px;
  border-radius: var(--radius-chip);
  color: var(--on-surface-variant);
  text-decoration: none;
  font-weight: 500;
  transition:
    background-color 0.15s ease,
    color 0.15s ease;
}

.tab:hover {
  background: color-mix(in srgb, var(--on-surface) 8%, transparent);
  color: var(--on-surface);
}

.tab--active {
  background: var(--primary-container);
  color: var(--on-primary-container);
}

.badge {
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  border-radius: var(--radius-chip);
  background: var(--warn-container);
  color: var(--warn);
  font-size: 12px;
  font-weight: 600;
  line-height: 20px;
  text-align: center;
}

.appbar__actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.appbar__freshness {
  color: var(--on-surface-muted);
  font-size: var(--font-size-label-md);
  line-height: var(--line-height-label-md);
  white-space: nowrap;
}

.refresh {
  width: 40px;
  height: 40px;
  padding: 0;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: var(--on-surface-variant);
  display: grid;
  place-items: center;
}

.refresh:hover:not(:disabled) {
  background: color-mix(in srgb, var(--on-surface) 8%, transparent);
  color: var(--on-surface);
}

.refresh:disabled {
  opacity: 0.5;
  cursor: default;
}

.refresh--spinning {
  animation: spin 0.9s linear infinite;
}

.progress {
  height: 2px;
  background: linear-gradient(
    90deg,
    transparent,
    var(--primary),
    transparent
  );
  background-size: 40% 100%;
  animation: progress 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@keyframes progress {
  from {
    background-position: -40% 0;
  }
  to {
    background-position: 140% 0;
  }
}

@media (max-width: 640px) {
  .appbar__inner {
    padding: 8px var(--space-4);
    gap: var(--space-3);
  }

  .brand__text {
    font-size: var(--font-size-title-md);
    line-height: var(--line-height-title-md);
  }

  .appbar__freshness {
    display: none;
  }
}
</style>
