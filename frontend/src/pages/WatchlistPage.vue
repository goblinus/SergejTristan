<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import StateBanner from '@/components/ui/StateBanner.vue';
import StatusFilterChips from '@/components/watchlist/StatusFilterChips.vue';
import TickerAutocomplete from '@/components/watchlist/TickerAutocomplete.vue';
import WatchlistList from '@/components/watchlist/WatchlistList.vue';
import { useWatchlist } from '@/composables/useWatchlist';
import type { WatchlistFilter, WatchlistItem } from '@/types/watchlist';
import { plural } from '@/utils/date';

const route = useRoute();
const router = useRouter();
const watchlist = useWatchlist();

const searchQuery = ref('');
const filter = ref<WatchlistFilter>('all');
const pendingTicker = ref<string | null>(null);
const searchRef = ref<InstanceType<typeof TickerAutocomplete> | null>(null);

const allItems = computed(() => watchlist.items.value ?? []);

const filteredItems = computed<WatchlistItem[]>(() => {
  const items = allItems.value;
  switch (filter.value) {
    case 'hot':
      return items.filter((item) => item.status === 'hot' || item.status === 'critical');
    case 'no_date':
      return items.filter((item) => item.status === 'no_date');
    case 'past':
      return items.filter((item) => item.status === 'past');
    default:
      return items;
  }
});

const countText = computed(() => {
  const count = allItems.value.length;
  if (!count) {
    return '';
  }
  return `${count} ${plural(count, ['тикер', 'тикера', 'тикеров'])}`;
});

const isEmpty = computed(
  () => watchlist.hasLoaded.value && !watchlist.isLoading.value && allItems.value.length === 0,
);

const isFilterEmpty = computed(
  () => !isEmpty.value && !watchlist.isLoading.value && filteredItems.value.length === 0,
);

function consumeTickerQuery(): void {
  const raw = route.query.ticker;
  const value = Array.isArray(raw) ? raw[0] : raw;
  if (!value) {
    return;
  }
  searchQuery.value = value.trim().toUpperCase();
  const query = { ...route.query };
  delete query.ticker;
  void router.replace({ query });
}

onMounted(() => {
  consumeTickerQuery();
  if (!watchlist.hasLoaded.value) {
    void watchlist.reload();
  }
});

watch(() => route.query.ticker, consumeTickerQuery);

async function addTicker(ticker: string): Promise<void> {
  const added = await watchlist.add(ticker);
  if (added) {
    searchQuery.value = '';
  }
}

async function removeTicker(ticker: string): Promise<void> {
  pendingTicker.value = ticker;
  try {
    await watchlist.remove(ticker);
  } finally {
    pendingTicker.value = null;
  }
}

function focusSearch(): void {
  searchRef.value?.focus();
}
</script>

<template>
  <section class="page">
    <div class="watch-head">
      <h1 class="page__title">Мои сторожки</h1>
      <span class="watch-head__count tabular">{{ countText }}</span>
    </div>
    <p class="page__lead">
      Сервис следит за датой отсечки выбранных тикеров. Когда до закрытия реестра останется
      меньше недели, карточка подсветится.
    </p>

    <TickerAutocomplete
      ref="searchRef"
      v-model="searchQuery"
      autofocus
      @add="addTicker"
    />

    <div class="watch-filters">
      <StatusFilterChips
        v-model="filter"
        :disabled="watchlist.isLoading.value || !watchlist.hasLoaded.value"
      />
    </div>

    <StateBanner
      v-if="watchlist.error.value && allItems.length === 0"
      variant="error"
      title="Не удалось загрузить сторожки"
      :text="watchlist.errorText.value ?? ''"
      action-label="Повторить"
      @action="watchlist.reload()"
    />

    <StateBanner
      v-else-if="watchlist.error.value && allItems.length > 0"
      variant="error"
      title="Данные могли устареть"
      :text="watchlist.errorText.value ?? ''"
      action-label="Повторить"
      @action="watchlist.reload()"
    />

    <WatchlistList
      v-if="!isEmpty && !isFilterEmpty"
      class="watch-list"
      :items="filteredItems"
      :is-loading="watchlist.isLoading.value && allItems.length === 0"
      :pending-ticker="pendingTicker"
      @remove="removeTicker"
    />

    <StateBanner
      v-if="isEmpty && !watchlist.error.value"
      class="watch-empty"
      variant="empty"
      title="Пока нет ни одного сторожка"
      text="Найдите тикер выше и нажмите «Отслеживать» — календарь покажет приближение даты отсечки."
      action-label="Найти тикер"
      @action="focusSearch"
    />

    <StateBanner
      v-else-if="isFilterEmpty && !watchlist.error.value"
      class="watch-empty"
      variant="empty"
      title="Под этот фильтр ничего не подходит"
      text="Снимите фильтр или выберите «Все»."
    />
  </section>
</template>

<style scoped>
.watch-head {
  display: flex;
  align-items: baseline;
  gap: var(--space-3);
}

.watch-head__count {
  color: var(--on-surface-muted);
}

.page__lead {
  margin-top: var(--space-2);
  color: var(--on-surface-variant);
  max-width: 720px;
}

.watch-filters {
  margin: var(--space-4) 0;
}

.watch-list,
.watch-empty {
  margin-top: var(--space-4);
}
</style>
