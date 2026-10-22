<script setup lang="ts">
withDefaults(
  defineProps<{
    variant?: 'card' | 'row' | 'fields';
    count?: number;
  }>(),
  { variant: 'card', count: 1 },
);
</script>

<template>
  <div class="skeleton" aria-hidden="true">
    <div v-for="index in count" :key="index" :class="['skeleton__item', `skeleton__item--${variant}`]">
      <template v-if="variant === 'card'">
        <div class="sk sk--logo" />
        <div class="sk sk--title" />
        <div class="sk sk--line" />
        <div class="sk sk--line short" />
        <div class="sk sk--chip" />
      </template>
      <template v-else-if="variant === 'row'">
        <div class="sk sk--logo" />
        <div class="sk sk--title" />
        <div class="sk sk--line" />
        <div class="sk sk--chip" />
      </template>
      <template v-else>
        <div class="sk sk--line" />
        <div class="sk sk--line short" />
        <div class="sk sk--line" />
      </template>
    </div>
  </div>
</template>

<style scoped>
.skeleton__item {
  position: relative;
  overflow: hidden;
  display: grid;
  gap: var(--space-2);
  padding: var(--space-4);
  background: var(--surface-2);
  border-radius: var(--radius-card);
}

.skeleton__item--row {
  grid-template-columns: 32px 1fr;
  align-items: center;
}

.sk {
  height: 12px;
  border-radius: 6px;
  background: var(--surface-3);
}

.sk--logo {
  width: 32px;
  height: 32px;
  border-radius: 8px;
}

.sk--title {
  width: 60%;
  height: 16px;
}

.sk--line {
  width: 100%;
}

.sk--line.short {
  width: 45%;
}

.sk--chip {
  width: 120px;
  height: 24px;
  border-radius: var(--radius-chip);
}

.skeleton__item::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(
    90deg,
    transparent,
    color-mix(in srgb, var(--on-surface) 6%, transparent),
    transparent
  );
  transform: translateX(-100%);
  animation: shimmer 1.2s infinite;
}

@keyframes shimmer {
  to {
    transform: translateX(100%);
  }
}
</style>
