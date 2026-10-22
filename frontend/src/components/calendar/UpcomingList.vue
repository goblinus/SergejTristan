<script setup lang="ts">
import TickerChip from '@/components/ui/TickerChip.vue';
import DeadlineIndicator from '@/components/ui/DeadlineIndicator.vue';
import type { UpcomingItemModel } from '@/composables/useCalendar';
import { estimateStatus } from '@/utils/deadline';
import { formatDate } from '@/utils/date';

defineProps<{
  items: UpcomingItemModel[];
}>();

const emit = defineEmits<{
  open: [id: number];
}>();

function open(item: UpcomingItemModel): void {
  if (item.meetingId !== null) {
    emit('open', item.meetingId);
  }
}
</script>

<template>
  <section v-if="items.length" class="section upcoming" aria-labelledby="upcomingListTitle">
    <div class="section__head">
      <h2 id="upcomingListTitle" class="section__title">Ближайшие отсечки</h2>
      <span class="section__count">{{ items.length }}</span>
    </div>
    <ul class="upcoming__list">
      <li v-for="item in items" :key="`${item.ticker}-${item.recordDate}`">
        <button
          v-if="item.meetingId !== null"
          type="button"
          class="upcoming__item"
          @click="open(item)"
        >
          <TickerChip :ticker="item.ticker" />
          <span class="upcoming__date tabular">{{ formatDate(item.recordDate) }}</span>
          <DeadlineIndicator
            :status="estimateStatus(item.daysToCutoff)"
            :days="item.daysToCutoff"
            compact
          />
        </button>
        <div v-else class="upcoming__item">
          <TickerChip :ticker="item.ticker" />
          <span class="upcoming__date tabular">{{ formatDate(item.recordDate) }}</span>
          <DeadlineIndicator
            :status="estimateStatus(item.daysToCutoff)"
            :days="item.daysToCutoff"
            compact
          />
        </div>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.upcoming__list {
  display: grid;
  gap: var(--space-1);
}

.upcoming__item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border: 0;
  border-radius: var(--radius-field);
  background: var(--surface-1);
  color: inherit;
  text-align: left;
}

button.upcoming__item:hover {
  background: var(--surface-2);
}

.upcoming__date {
  color: var(--on-surface-variant);
  font-feature-settings: 'tnum';
}

.upcoming__item :deep(.deadline) {
  margin-left: auto;
}
</style>
