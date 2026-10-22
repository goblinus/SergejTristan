<script setup lang="ts">
import { computed } from 'vue';

import CompanyFacts from '@/components/company/CompanyFacts.vue';
import CompanyIdentity from '@/components/company/CompanyIdentity.vue';
import DsiBadge from '@/components/dividend/DsiBadge.vue';
import DeadlineIndicator from '@/components/ui/DeadlineIndicator.vue';
import type { MeetingCardModel } from '@/composables/useCalendar';
import { formatDate } from '@/utils/date';
import { formatMoney, formatPercent, formatPeriod } from '@/utils/formatDividend';

const props = defineProps<{
  card: MeetingCardModel;
}>();

const emit = defineEmits<{
  open: [id: number];
}>();

const meeting = computed(() => props.card.meeting);
const isPast = computed(() => props.card.status === 'past');
const dividend = computed(() => meeting.value.dividend);

const ariaLabel = computed(() => {
  const m = meeting.value;
  return `${m.ticker}, ${m.short_name}. Период: ${formatPeriod(dividend.value?.period ?? null)}. ` +
    `На акцию: ${formatMoney(dividend.value?.amount_per_share ?? null)}. ` +
    `Доходность: ${formatPercent(dividend.value?.yield_percent ?? null)}. ` +
    `Отсечка: ${props.card.recordDate ? formatDate(props.card.recordDate) : 'не объявлена'}.`;
});

function open(): void {
  emit('open', meeting.value.id);
}

function onClick(event: MouseEvent): void {
  if ((event.target as Element | null)?.closest('.dsi__hint')) {
    return;
  }
  open();
}

function onKeydown(event: KeyboardEvent): void {
  if ((event.target as Element | null)?.closest('.dsi__hint')) {
    return;
  }
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault();
    open();
  }
}
</script>

<template>
  <article
    :class="['card', { 'card--past': isPast }]"
    role="button"
    tabindex="0"
    :aria-label="ariaLabel"
    @click="onClick"
    @keydown="onKeydown"
  >
    <div class="card__head">
      <CompanyIdentity
        :logo-url="meeting.logo_url"
        :ticker="meeting.ticker"
        :name="meeting.short_name"
        :watched="card.watched"
      />
    </div>

    <CompanyFacts
      :period="dividend?.period ?? null"
      :amount-per-share="dividend?.amount_per_share ?? null"
      :yield-percent="dividend?.yield_percent ?? null"
      :meeting-date="meeting.meeting_date"
      :cutoff-date="card.recordDate"
    />

    <div class="card__foot">
      <DeadlineIndicator :status="card.status" :days="card.daysToCutoff" />
      <DsiBadge :value="meeting.dsi" />
    </div>
  </article>
</template>

<style scoped>
.card {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-4);
  background: var(--surface-2);
  border-radius: var(--radius-card);
  border: 1px solid transparent;
  cursor: pointer;
  transition:
    background-color 0.15s ease,
    transform 0.15s ease;
}

.card:hover {
  background: var(--surface-3);
  transform: translateY(-1px);
}

.card--past {
  opacity: 0.6;
}

.card--past:hover {
  opacity: 0.8;
}

.card__foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding-top: var(--space-3);
  border-top: 1px solid var(--outline-variant);
}

@media (max-width: 640px) {
  .card {
    padding: var(--space-3);
  }
}
</style>
