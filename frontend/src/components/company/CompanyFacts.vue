<script setup lang="ts">
import { computed } from 'vue';

import type { DividendPeriod } from '@/types/dividend';
import { formatDate } from '@/utils/date';
import { formatMoney, formatPercent, formatPeriod } from '@/utils/formatDividend';

const props = defineProps<{
  period: DividendPeriod | null;
  amountPerShare: number | null;
  yieldPercent: number | null;
  meetingDate: string | null;
  cutoffDate: string | null;
}>();

const facts = computed(() => [
  { label: 'Период', value: formatPeriod(props.period) },
  { label: 'На акцию', value: formatMoney(props.amountPerShare) },
  { label: 'Доходность', value: formatPercent(props.yieldPercent) },
  { label: 'Собрание', value: props.meetingDate ? formatDate(props.meetingDate) : '—' },
  { label: 'Отсечка', value: props.cutoffDate ? formatDate(props.cutoffDate) : '—' },
]);
</script>

<template>
  <dl class="facts">
    <div v-for="fact in facts" :key="fact.label" class="facts__cell">
      <dt class="facts__label">{{ fact.label }}</dt>
      <dd class="facts__value tabular">{{ fact.value }}</dd>
    </div>
  </dl>
</template>

<style scoped>
.facts {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: var(--space-2);
}

.facts__cell {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.facts__label {
  color: var(--on-surface-muted);
  font-size: 10px;
  line-height: 12px;
  white-space: nowrap;
}

.facts__value {
  color: var(--on-surface);
  font-size: 12.5px;
  line-height: 18px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-feature-settings: 'tnum';
}

@media (max-width: 640px) {
  .facts__label {
    font-size: 9.5px;
    line-height: 11px;
  }

  .facts__value {
    font-size: 11.5px;
    line-height: 16px;
  }
}
</style>
