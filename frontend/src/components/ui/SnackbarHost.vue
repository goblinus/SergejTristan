<script setup lang="ts">
import { useSnackbar } from '@/composables/useSnackbar';

import AppIcon from './AppIcon.vue';

const snackbar = useSnackbar();
</script>

<template>
  <div
    v-if="snackbar.visible.value && snackbar.current.value"
    class="snackbar"
    role="status"
    aria-live="polite"
    @mouseenter="snackbar.pause"
    @mouseleave="snackbar.resume"
  >
    <AppIcon
      :name="snackbar.current.value.kind === 'success' ? 'check_circle' : 'error'"
      :size="20"
      :class="['snackbar__icon', `snackbar__icon--${snackbar.current.value.kind}`]"
    />
    <span class="snackbar__text">{{ snackbar.current.value.text }}</span>
    <button
      v-if="snackbar.current.value.action"
      class="snackbar__action"
      type="button"
      @click="snackbar.runAction"
    >
      {{ snackbar.current.value.action.label }}
    </button>
  </div>
</template>

<style scoped>
.snackbar {
  position: fixed;
  left: 50%;
  bottom: var(--space-6);
  transform: translateX(-50%);
  z-index: var(--z-snackbar);
  display: flex;
  align-items: center;
  gap: var(--space-3);
  min-width: 280px;
  max-width: min(560px, calc(100vw - 32px));
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-snack);
  background: var(--surface-3);
  border: 1px solid var(--outline-variant);
  box-shadow: var(--shadow-modal);
}

.snackbar__icon--success {
  color: var(--success);
}

.snackbar__icon--error {
  color: var(--danger);
}

.snackbar__text {
  flex: 1;
}

.snackbar__action {
  border: 0;
  background: transparent;
  color: var(--primary);
  font-weight: 600;
  padding: var(--space-1) var(--space-2);
  border-radius: 6px;
}

.snackbar__action:hover {
  background: color-mix(in srgb, var(--on-surface) 8%, transparent);
}

@media (max-width: 640px) {
  .snackbar {
    bottom: 96px;
  }
}
</style>
