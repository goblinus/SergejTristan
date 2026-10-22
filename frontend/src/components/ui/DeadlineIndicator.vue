<script setup lang="ts">
import { computed } from 'vue';

import type { WatchStatus } from '@/types/watchlist';
import { formatDaysLabel } from '@/utils/date';

import AppIcon from './AppIcon.vue';
import type { IconName } from './iconPaths';

const props = withDefaults(
  defineProps<{
    status: WatchStatus;
    days: number | null;
    compact?: boolean;
  }>(),
  { compact: false },
);

const ICONS: Record<WatchStatus, IconName> = {
  no_date: 'event_busy',
  far: 'schedule',
  near: 'event_upcoming',
  hot: 'warning',
  critical: 'priority_high',
  past: 'event_available',
};

const icon = computed(() => ICONS[props.status]);

const text = computed(() => {
  const days = props.days;
  switch (props.status) {
    case 'no_date':
      return 'нет даты';
    case 'past':
      return 'прошла';
    case 'critical':
      return 'сегодня!';
    case 'hot':
      return props.compact ? `осталось ${days ?? 0} дн.` : `${formatDaysLabel(days ?? 0)} до отсечки`;
    case 'near':
    case 'far':
      return props.compact ? `${days ?? 0} дн.` : `${formatDaysLabel(days ?? 0)} до отсечки`;
    default:
      return '';
  }
});
</script>

<template>
  <span :class="['deadline', `deadline--${status}`]" :title="text">
    <AppIcon :name="icon" :size="16" />
    <span class="deadline__text tabular">{{ text }}</span>
  </span>
</template>

<style scoped>
.deadline {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: var(--radius-chip);
  font-size: var(--font-size-label-md);
  line-height: var(--line-height-label-md);
  font-weight: 500;
  white-space: nowrap;
}

.deadline--no_date {
  background: var(--neutral-chip);
  color: var(--on-surface-variant);
}

.deadline--far {
  background: var(--surface-3);
  color: var(--on-surface);
}

.deadline--near {
  background: var(--primary-container);
  color: var(--on-primary-container);
}

.deadline--hot {
  background: var(--warn-container);
  color: var(--warn);
}

.deadline--critical {
  background: var(--danger-container);
  color: var(--danger);
}

.deadline--past {
  background: var(--surface-1);
  color: var(--on-surface-muted);
  border: 1px solid var(--outline-variant);
}

.deadline__text {
  font-feature-settings: 'tnum';
}
</style>
