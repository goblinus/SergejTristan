<script setup lang="ts">
import Skeleton from '@/components/ui/Skeleton.vue';
import type { WatchlistItem } from '@/types/watchlist';

import WatchRow from './WatchRow.vue';

defineProps<{
  items: WatchlistItem[];
  isLoading: boolean;
  pendingTicker?: string | null;
}>();

defineEmits<{
  remove: [ticker: string];
}>();
</script>

<template>
  <Skeleton v-if="isLoading" variant="row" :count="4" />
  <ul v-else-if="items.length" class="watch-list">
    <WatchRow
      v-for="item in items"
      :key="item.ticker"
      :item="item"
      :pending="pendingTicker === item.ticker"
      @remove="$emit('remove', $event)"
    />
  </ul>
</template>

<style scoped>
.watch-list {
  display: grid;
  gap: var(--space-2);
}
</style>
