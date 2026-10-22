import { computed, reactive, ref, watch, type Ref } from 'vue';

import { getMeetings } from '@/api/endpoints/meetings';
import { getRecordDates } from '@/api/endpoints/record-dates';
import { ApiError } from '@/api/errors';
import type { Meeting } from '@/types/meeting';
import type { RecordDate } from '@/types/record-date';
import type { WatchStatus } from '@/types/watchlist';
import { minTimestamp, monthRange, daysUntil, todayIso } from '@/utils/date';
import { estimateStatus } from '@/utils/deadline';

import { useConnectivity } from './useConnectivity';
import { useWatchlist } from './useWatchlist';

interface MonthCacheEntry {
  meetings: Meeting[];
  recordDates: RecordDate[];
  loadedAt: number;
}

export interface MeetingCardModel {
  meeting: Meeting;
  recordDate: string | null;
  daysToCutoff: number | null;
  status: WatchStatus;
  watched: boolean;
}

export interface UpcomingItemModel {
  ticker: string;
  recordDate: string;
  meetingId: number | null;
  daysToCutoff: number;
}

interface CalendarState {
  isLoading: boolean;
  error: ApiError | null;
}

const cache = reactive(new Map<string, MonthCacheEntry>());
const requestedMonth = ref(todayIso().slice(0, 7));
const state = reactive<CalendarState>({ isLoading: false, error: null });

export function findCachedMeeting(id: number): Meeting | null {
  for (const entry of cache.values()) {
    const found = entry.meetings.find((meeting) => meeting.id === id);
    if (found) {
      return found;
    }
  }
  return null;
}

/** Свежесть данных календаря для индикатора в AppHeader. */
export function useCalendarFreshness() {
  return computed(() => {
    const entry = cache.get(requestedMonth.value);
    if (!entry) {
      return null;
    }
    return minTimestamp([
      ...entry.meetings.map((meeting) => meeting.fetched_at),
      ...entry.recordDates.map((record) => record.fetched_at),
    ]);
  });
}

/** Состояние загрузки календаря для полосы прогресса в AppHeader. */
export function useCalendarLoading() {
  return computed(() => state.isLoading);
}

/** Принудительное обновление текущего месяца (кнопка «Обновить»). */
export function reloadCalendar(): Promise<void> {
  return load(requestedMonth.value, true);
}

const CACHE_TTL_MS = 60 * 60 * 1000;
let loadToken = 0;

async function load(month: string, force: boolean): Promise<void> {
  requestedMonth.value = month;
  const cached = cache.get(month);
  if (!force && cached && Date.now() - cached.loadedAt < CACHE_TTL_MS) {
    state.error = null;
    return;
  }

  const connectivity = useConnectivity();
  const token = ++loadToken;
  state.isLoading = true;
  state.error = null;
  const { from, to } = monthRange(month);

  try {
    const [meetingsPage, recordDatesPage] = await Promise.all([
      getMeetings({ from, to, page: 1, page_size: 100 }),
      getRecordDates({ from, to, kind: 'dividend_payment', page: 1, page_size: 100 }),
    ]);
    cache.set(month, {
      meetings: meetingsPage.items,
      recordDates: recordDatesPage.items,
      loadedAt: Date.now(),
    });
    if (token === loadToken) {
      connectivity.reportSuccess();
    }
  } catch (error) {
    if (token === loadToken) {
      state.error =
        error instanceof ApiError ? error : new ApiError('network', 'Ошибка загрузки');
      connectivity.reportError(error);
    }
  } finally {
    if (token === loadToken) {
      state.isLoading = false;
    }
  }
}

/** Объединённый кэш собраний и отсечек выбранного месяца. */
export function useCalendar(month: Ref<string>) {
  const watchlist = useWatchlist();

  watch(month, (value) => void load(value, false), { immediate: true });

  const entry = computed(() => cache.get(requestedMonth.value) ?? null);
  const meetings = computed(() => entry.value?.meetings ?? []);
  const recordDates = computed(() => entry.value?.recordDates ?? []);

  const cards = computed<MeetingCardModel[]>(() => {
    const items = watchlist.items.value ?? [];
    const byTicker = new Map(items.map((item) => [item.ticker, item]));

    return meetings.value
      .map((meeting) => {
        const recordDate = meeting.record_date?.record_date ?? null;
        const localDays = recordDate === null ? null : daysUntil(recordDate);
        const watchedItem = byTicker.get(meeting.ticker) ?? null;
        return {
          meeting,
          recordDate,
          daysToCutoff: watchedItem?.days_to_cutoff ?? localDays,
          status: watchedItem?.status ?? estimateStatus(localDays),
          watched: watchedItem !== null,
        };
      })
      .sort((a, b) => a.meeting.meeting_date.localeCompare(b.meeting.meeting_date));
  });

  function isPastCard(card: MeetingCardModel): boolean {
    if (card.daysToCutoff !== null) {
      return card.daysToCutoff < 0;
    }
    return daysUntil(card.meeting.meeting_date) < 0;
  }

  const upcomingCards = computed(() => cards.value.filter((card) => !isPastCard(card)));
  const pastCards = computed(() => cards.value.filter(isPastCard));

  const upcoming = computed<UpcomingItemModel[]>(() =>
    recordDates.value
      .map((record) => ({
        ticker: record.ticker,
        recordDate: record.record_date,
        meetingId: record.meeting_id,
        daysToCutoff: daysUntil(record.record_date),
      }))
      .filter((record) => record.daysToCutoff >= 0)
      .sort((a, b) => a.recordDate.localeCompare(b.recordDate)),
  );

  const fetchedAtMin = computed(() =>
    minTimestamp([
      ...meetings.value.map((meeting) => meeting.fetched_at),
      ...recordDates.value.map((record) => record.fetched_at),
    ]),
  );

  return {
    month: requestedMonth,
    isLoading: computed(() => state.isLoading),
    error: computed(() => state.error),
    errorText: computed(() => state.error?.detail ?? null),
    meetings,
    recordDates,
    cards,
    upcomingCards,
    pastCards,
    upcoming,
    fetchedAtMin,
    reload: () => load(requestedMonth.value, true),
  };
}
