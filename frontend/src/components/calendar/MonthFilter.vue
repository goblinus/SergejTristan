<script setup lang="ts">
import AppIcon from '@/components/ui/AppIcon.vue';

defineProps<{
  monthLabel: string;
  showPast: boolean;
  foundText: string;
}>();

defineEmits<{
  prev: [];
  next: [];
  'update:showPast': [value: boolean];
}>();
</script>

<template>
  <div class="toolbar">
    <div class="monthswitch" role="group" aria-label="Выбор месяца">
      <button
        class="monthswitch__btn"
        type="button"
        aria-label="Предыдущий месяц"
        @click="$emit('prev')"
      >
        <AppIcon name="chevron_left" :size="20" />
      </button>
      <span class="monthswitch__label" aria-live="polite">{{ monthLabel }}</span>
      <button
        class="monthswitch__btn"
        type="button"
        aria-label="Следующий месяц"
        @click="$emit('next')"
      >
        <AppIcon name="chevron_right" :size="20" />
      </button>
    </div>

    <label class="checkbox">
      <input
        type="checkbox"
        :checked="showPast"
        @change="$emit('update:showPast', ($event.target as HTMLInputElement).checked)"
      />
      <span class="checkbox__full">Показать прошедшие</span>
      <span class="checkbox__short">Прошедшие</span>
    </label>

    <p class="toolbar__meta">{{ foundText }}</p>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  flex-wrap: wrap;
}

.monthswitch {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  background: var(--surface-1);
  border: 1px solid var(--outline-variant);
  border-radius: var(--radius-chip);
  padding: 2px;
}

.monthswitch__btn {
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: var(--on-surface-variant);
}

.monthswitch__btn:hover {
  background: color-mix(in srgb, var(--on-surface) 8%, transparent);
  color: var(--on-surface);
}

.monthswitch__label {
  min-width: 132px;
  text-align: center;
  font-weight: 600;
}

.checkbox {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--on-surface-variant);
  cursor: pointer;
}

.checkbox input {
  width: 16px;
  height: 16px;
  accent-color: var(--primary);
}

.checkbox__short {
  display: none;
}

.toolbar__meta {
  color: var(--on-surface-muted);
  font-size: var(--font-size-body-md);
}

@media (max-width: 640px) {
  .checkbox__full {
    display: none;
  }

  .checkbox__short {
    display: inline;
  }

  .toolbar__meta {
    flex-basis: 100%;
  }
}
</style>
