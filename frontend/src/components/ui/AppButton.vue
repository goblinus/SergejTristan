<script setup lang="ts">
withDefaults(
  defineProps<{
    variant?: 'filled' | 'tonal' | 'text' | 'icon';
    size?: 'md' | 'sm';
    type?: 'button' | 'submit';
    disabled?: boolean;
    loading?: boolean;
  }>(),
  {
    variant: 'text',
    size: 'md',
    type: 'button',
    disabled: false,
    loading: false,
  },
);

defineEmits<{
  click: [event: MouseEvent];
}>();
</script>

<template>
  <button
    :type="type"
    :class="['btn', `btn--${variant}`, `btn--${size}`]"
    :disabled="disabled || loading"
    :aria-busy="loading || undefined"
    @click="$emit('click', $event)"
  >
    <span v-if="loading" class="btn__spinner" aria-hidden="true" />
    <span :class="['btn__label', { 'btn__label--hidden': loading }]"><slot /></span>
  </button>
</template>

<style scoped>
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  border: 0;
  border-radius: var(--radius-button);
  font-size: var(--font-size-label-lg);
  line-height: var(--line-height-label-lg);
  font-weight: 500;
  padding: 0 var(--space-4);
  min-height: 40px;
  transition:
    background-color 0.15s ease,
    color 0.15s ease,
    opacity 0.15s ease;
}

.btn--sm {
  min-height: 32px;
  padding: 0 var(--space-3);
  font-size: var(--font-size-label-md);
  line-height: var(--line-height-label-md);
}

.btn--filled {
  background: var(--primary);
  color: var(--on-primary);
}

.btn--filled:hover:not(:disabled) {
  background: color-mix(in srgb, var(--primary) 88%, white);
}

.btn--tonal {
  background: var(--primary-container);
  color: var(--on-primary-container);
}

.btn--tonal:hover:not(:disabled) {
  background: color-mix(in srgb, var(--primary-container) 85%, white);
}

.btn--text {
  background: transparent;
  color: var(--primary);
}

.btn--text:hover:not(:disabled) {
  background: color-mix(in srgb, var(--on-surface) 8%, transparent);
}

.btn--icon {
  width: 40px;
  min-height: 40px;
  padding: 0;
  border-radius: 50%;
  background: transparent;
  color: var(--on-surface-variant);
}

.btn--icon.btn--sm {
  width: 32px;
  min-height: 32px;
}

.btn--icon:hover:not(:disabled) {
  background: color-mix(in srgb, var(--on-surface) 8%, transparent);
  color: var(--on-surface);
}

.btn:disabled {
  opacity: 0.38;
  cursor: default;
}

.btn__label--hidden {
  visibility: hidden;
}

.btn__spinner {
  position: absolute;
  width: 16px;
  height: 16px;
  border: 2px solid currentColor;
  border-right-color: transparent;
  border-radius: 50%;
  animation: btn-spin 0.7s linear infinite;
}

.btn {
  position: relative;
}

@keyframes btn-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
