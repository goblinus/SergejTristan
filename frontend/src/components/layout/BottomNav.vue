<script setup lang="ts">
import { useRoute } from 'vue-router';

import AppIcon from '@/components/ui/AppIcon.vue';

withDefaults(
  defineProps<{
    hotCount?: number;
    hasWatchlistLoaded?: boolean;
  }>(),
  { hotCount: 0, hasWatchlistLoaded: false },
);

const route = useRoute();
</script>

<template>
  <nav class="bottom-nav" aria-label="Основная навигация">
    <RouterLink
      :to="{ name: 'calendar' }"
      :class="['bottom-nav__item', { 'bottom-nav__item--active': route.name === 'calendar' }]"
    >
      <AppIcon name="calendar_month" :size="24" />
      <span>Календарь</span>
    </RouterLink>
    <RouterLink
      :to="{ name: 'me' }"
      :class="['bottom-nav__item', { 'bottom-nav__item--active': route.name === 'me' }]"
    >
      <span class="bottom-nav__icon-wrap">
        <AppIcon name="notifications_active" :size="24" />
        <span
          v-if="(hotCount ?? 0) > 0 && hasWatchlistLoaded"
          class="badge tabular"
          aria-label="Горячих сторожков"
        >
          {{ hotCount ?? 0 }}
        </span>
      </span>
      <span>Сторожки</span>
    </RouterLink>
  </nav>
</template>

<style scoped>
.bottom-nav {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: var(--z-header);
  display: flex;
  background: var(--surface-1);
  border-top: 1px solid var(--outline-variant);
}

.bottom-nav__item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: var(--space-2) 0 var(--space-3);
  color: var(--on-surface-variant);
  text-decoration: none;
  font-size: var(--font-size-label-md);
  line-height: var(--line-height-label-md);
}

.bottom-nav__item--active {
  color: var(--on-primary-container);
  background: var(--primary-container);
}

.bottom-nav__icon-wrap {
  position: relative;
  display: inline-flex;
}

.badge {
  position: absolute;
  top: -6px;
  right: -10px;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: var(--radius-chip);
  background: var(--warn-container);
  color: var(--warn);
  font-size: 11px;
  font-weight: 600;
  line-height: 18px;
  text-align: center;
}
</style>
