<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { useRoute } from 'vue-router';

import AppHeader from '@/components/layout/AppHeader.vue';
import BottomNav from '@/components/layout/BottomNav.vue';
import SnackbarHost from '@/components/ui/SnackbarHost.vue';
import StateBanner from '@/components/ui/StateBanner.vue';
import {
  reloadCalendar,
  useCalendarFreshness,
  useCalendarLoading,
} from '@/composables/useCalendar';
import { useConnectivity } from '@/composables/useConnectivity';
import { useMediaQuery } from '@/composables/useMediaQuery';
import { useWatchlist } from '@/composables/useWatchlist';
import { formatFreshness } from '@/utils/date';

const route = useRoute();
const isMobile = useMediaQuery('(max-width: 640px)');
const watchlist = useWatchlist();
const connectivity = useConnectivity();
const calendarLoading = useCalendarLoading();
const calendarFreshness = useCalendarFreshness();

const isCalendar = computed(() => route.name === 'calendar');
const isWatchlist = computed(() => route.name === 'me');

const isLoading = computed(() =>
  isCalendar.value ? calendarLoading.value : isWatchlist.value ? watchlist.isLoading.value : false,
);

const freshness = computed(() => formatFreshness(calendarFreshness.value));

onMounted(() => {
  void watchlist.reload();
});

async function refresh(): Promise<void> {
  if (isWatchlist.value) {
    await watchlist.reload();
    return;
  }
  if (isCalendar.value) {
    await reloadCalendar();
  }
}
</script>

<template>
  <a class="skip-link" href="#main">Перейти к содержимому</a>

  <AppHeader
    :freshness="freshness"
    :is-loading="isLoading"
    :hot-count="watchlist.hotCount.value"
    :has-watchlist-loaded="watchlist.hasLoaded.value"
    :show-watchlist-tabs="!isMobile"
    @refresh="refresh"
  />

  <div v-if="connectivity.isOffline.value" class="offline">
    <StateBanner
      variant="offline"
      title="Нет соединения"
      text="Показаны последние загруженные данные — они могли устареть."
    />
  </div>

  <main id="main" tabindex="-1">
    <RouterView />
  </main>

  <BottomNav
    v-if="isMobile"
    :hot-count="watchlist.hotCount.value"
    :has-watchlist-loaded="watchlist.hasLoaded.value"
  />

  <SnackbarHost />
</template>

<style scoped>
.offline {
  max-width: var(--content-max);
  margin: var(--space-4) auto 0;
  padding: 0 var(--space-6);
}

@media (max-width: 640px) {
  .offline {
    padding: 0 var(--space-4);
  }
}
</style>
