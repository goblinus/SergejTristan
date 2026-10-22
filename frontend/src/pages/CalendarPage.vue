<script setup lang="ts">
import { computed, ref } from 'vue';

import MeetingDetailsDialog from '@/components/calendar/MeetingDetailsDialog.vue';
import MeetingsGrid from '@/components/calendar/MeetingsGrid.vue';
import MonthFilter from '@/components/calendar/MonthFilter.vue';
import UpcomingList from '@/components/calendar/UpcomingList.vue';
import Skeleton from '@/components/ui/Skeleton.vue';
import StateBanner from '@/components/ui/StateBanner.vue';
import { useCalendar } from '@/composables/useCalendar';
import { useMeetingDialog } from '@/composables/useMeetingDialog';
import { addMonths, formatFreshness, monthTitle, plural, todayIso } from '@/utils/date';

const month = ref(todayIso().slice(0, 7));
const showPast = ref(false);

const calendar = useCalendar(month);
const dialog = useMeetingDialog();

const monthLabel = computed(() => monthTitle(month.value));

const totalFound = computed(
  () => calendar.upcomingCards.value.length + calendar.pastCards.value.length,
);

const foundText = computed(() => {
  if (calendar.isLoading.value && calendar.cards.value.length === 0) {
    return 'Загружаем данные…';
  }
  if (totalFound.value === 0) {
    return 'Ничего не найдено';
  }
  const found = `Найдено: ${totalFound.value} ${plural(totalFound.value, [
    'собрание',
    'собрания',
    'собраний',
  ])}`;
  const freshness = formatFreshness(calendar.fetchedAtMin.value);
  return freshness ? `${found} · ${freshness}` : found;
});

const bothEmpty = computed(
  () => calendar.upcomingCards.value.length === 0 && calendar.pastCards.value.length === 0,
);

const allPastHidden = computed(
  () =>
    calendar.upcomingCards.value.length === 0 &&
    calendar.pastCards.value.length > 0 &&
    !showPast.value,
);

const emptyTitle = computed(() => {
  if (allPastHidden.value) {
    return 'Все собрания этого месяца уже прошли';
  }
  return 'В этом месяце собраний нет';
});

const emptyText = computed(() => {
  if (allPastHidden.value) {
    return 'Включите «Показать прошедшие», чтобы увидеть их в списке.';
  }
  return 'Переключите месяц стрелками или включите «Показать прошедшие».';
});

function shiftMonth(delta: number): void {
  month.value = addMonths(month.value, delta);
}

function openMeeting(id: number): void {
  dialog.open(id);
}
</script>

<template>
  <section class="page">
    <h1 class="visually-hidden">Календарь собраний</h1>

    <MonthFilter
      v-model:show-past="showPast"
      :month-label="monthLabel"
      :found-text="foundText"
      @prev="shiftMonth(-1)"
      @next="shiftMonth(1)"
    />

    <StateBanner
      v-if="calendar.error.value"
      class="calendar__error"
      variant="error"
      title="Не удалось загрузить календарь"
      :text="calendar.errorText.value ?? ''"
      action-label="Повторить"
      @action="calendar.reload()"
    />

    <Skeleton
      v-if="calendar.isLoading.value && calendar.cards.value.length === 0"
      class="calendar__skeleton"
      variant="card"
      :count="6"
    />

    <template v-else>
      <div class="section__head calendar__head">
        <h2 class="section__title">Предстоящие</h2>
        <span v-if="calendar.upcomingCards.value.length" class="section__count">
          {{ calendar.upcomingCards.value.length }}
        </span>
      </div>

      <MeetingsGrid
        v-if="calendar.upcomingCards.value.length"
        :cards="calendar.upcomingCards.value"
        @open="openMeeting"
      />

      <StateBanner
        v-else-if="bothEmpty || allPastHidden"
        class="calendar__empty"
        variant="empty"
        :title="emptyTitle"
        :text="emptyText"
        :action-label="allPastHidden ? 'Показать прошедшие' : ''"
        @action="showPast = true"
      />

      <UpcomingList :items="calendar.upcoming.value" @open="openMeeting" />

      <section v-if="showPast && calendar.pastCards.value.length" class="section">
        <div class="section__head">
          <h2 class="section__title">Прошедшие</h2>
          <span class="section__count">{{ calendar.pastCards.value.length }}</span>
        </div>
        <MeetingsGrid :cards="calendar.pastCards.value" @open="openMeeting" />
      </section>
    </template>

    <MeetingDetailsDialog
      v-if="dialog.isOpen.value"
      :meeting="dialog.meeting.value"
      :is-loading="dialog.isLoading.value"
      :not-found="dialog.notFound.value"
      :error-text="dialog.errorText.value"
      @close="dialog.close"
      @retry="dialog.retry"
    />
  </section>
</template>

<style scoped>
.calendar__error,
.calendar__skeleton,
.calendar__empty {
  margin-top: var(--space-4);
}

.calendar__head {
  margin-top: var(--space-6);
}
</style>
