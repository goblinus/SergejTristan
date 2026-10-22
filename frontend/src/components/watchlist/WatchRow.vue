<script setup lang="ts">
import { computed } from 'vue';

import CompanyFacts from '@/components/company/CompanyFacts.vue';
import CompanyIdentity from '@/components/company/CompanyIdentity.vue';
import DsiBadge from '@/components/dividend/DsiBadge.vue';
import AppIcon from '@/components/ui/AppIcon.vue';
import DeadlineIndicator from '@/components/ui/DeadlineIndicator.vue';
import type { WatchlistItem } from '@/types/watchlist';

const props = defineProps<{
  item: WatchlistItem;
  pending?: boolean;
}>();

const emit = defineEmits<{
  remove: [ticker: string];
}>();

const isPast = computed(() => props.item.status === 'past');
const dividend = computed(() => props.item.next_dividend);

function requestRemove(): void {
  if (props.item.status === 'hot' || props.item.status === 'critical') {
    const confirmed = window.confirm(
      `Сторожок ${props.item.ticker} в горячей зоне. Снять отслеживание?`,
    );
    if (!confirmed) {
      return;
    }
  }
  emit('remove', props.item.ticker);
}
</script>

<template>
  <li :class="['row', { 'row--past': isPast, 'row--pending': pending }]">
    <div class="row__head">
      <CompanyIdentity
        :logo-url="item.logo_url"
        :ticker="item.ticker"
        :name="item.short_name"
      />
      <button
        class="row__remove"
        type="button"
        :disabled="pending"
        :aria-label="`Убрать ${item.ticker} из сторожков`"
        title="Убрать из сторожков"
        @click="requestRemove"
      >
        <span v-if="pending" class="row__spinner" aria-hidden="true" />
        <AppIcon v-else name="delete" :size="20" />
      </button>
    </div>

    <CompanyFacts
      :period="dividend?.period ?? null"
      :amount-per-share="dividend?.amount_per_share ?? null"
      :yield-percent="dividend?.yield_percent ?? null"
      :meeting-date="item.next_meeting_date"
      :cutoff-date="item.next_record_date"
    />

    <div class="row__foot">
      <DeadlineIndicator :status="item.status" :days="item.days_to_event" compact />
      <DsiBadge :value="item.dsi" />
    </div>
  </li>
</template>

<style scoped>
.row {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-4);
  background: var(--surface-2);
  border-radius: var(--radius-card);
}

.row--past {
  opacity: 0.6;
}

.row--pending {
  opacity: 0.5;
}

.row__head {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.row__head :deep(.identity) {
  flex: 1;
}

.row__remove {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: var(--on-surface-muted);
}

.row__remove:hover:not(:disabled) {
  background: color-mix(in srgb, var(--on-surface) 8%, transparent);
  color: var(--danger);
}

.row__remove:disabled {
  cursor: default;
}

.row__spinner {
  width: 16px;
  height: 16px;
  border: 2px solid var(--on-surface-muted);
  border-right-color: transparent;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

.row__foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding-top: var(--space-3);
  border-top: 1px solid var(--outline-variant);
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (min-width: 641px) {
  .row :deep(.facts) {
    max-width: 720px;
  }
}
</style>
