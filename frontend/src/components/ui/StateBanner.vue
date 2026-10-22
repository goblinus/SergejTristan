<script setup lang="ts">
import AppButton from './AppButton.vue';
import AppIcon from './AppIcon.vue';
import type { IconName } from './iconPaths';

withDefaults(
  defineProps<{
    variant?: 'empty' | 'error' | 'offline';
    title: string;
    text?: string;
    actionLabel?: string;
  }>(),
  { variant: 'empty', text: '', actionLabel: '' },
);

defineEmits<{
  action: [];
}>();

const ICONS: Record<'empty' | 'error' | 'offline', IconName> = {
  empty: 'event_busy',
  error: 'error',
  offline: 'warning',
};
</script>

<template>
  <div :class="['banner', `banner--${variant}`]" role="status" aria-live="polite">
    <AppIcon :name="ICONS[variant ?? 'empty']" :size="24" />
    <div class="banner__body">
      <p class="banner__title">{{ title }}</p>
      <p v-if="text" class="banner__text">{{ text }}</p>
    </div>
    <AppButton v-if="actionLabel" variant="tonal" size="sm" @click="$emit('action')">
      {{ actionLabel }}
    </AppButton>
  </div>
</template>

<style scoped>
.banner {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4);
  border-radius: var(--radius-card);
  background: var(--surface-1);
  border: 1px solid var(--outline-variant);
  color: var(--on-surface-variant);
}

.banner--error {
  border-color: var(--danger-container);
}

.banner--error > :first-child {
  color: var(--danger);
}

.banner--offline {
  background: var(--warn-container);
  border-color: var(--warn-container);
  color: var(--warn);
}

.banner__body {
  flex: 1;
  display: grid;
  gap: 2px;
}

.banner__title {
  color: var(--on-surface);
  font-weight: 600;
}

.banner__text {
  font-size: var(--font-size-body-md);
}
</style>
