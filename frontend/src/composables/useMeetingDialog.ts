import { computed, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { getMeeting } from '@/api/endpoints/meetings';
import { ApiError } from '@/api/errors';
import type { Meeting } from '@/types/meeting';

import { findCachedMeeting } from './useCalendar';

/** Модал деталей собрания, привязанный к query `?meeting=<id>`. */
export function useMeetingDialog() {
  const route = useRoute();
  const router = useRouter();

  const meetingId = computed<number | null>(() => {
    const raw = route.query.meeting;
    const value = Array.isArray(raw) ? raw[0] : raw;
    if (value === undefined || value === null || value === '') {
      return null;
    }
    const parsed = Number(value);
    return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
  });

  const meeting = ref<Meeting | null>(null);
  const isLoading = ref(false);
  const notFound = ref(false);
  const error = ref<ApiError | null>(null);
  let requestedId: number | null = null;

  async function load(id: number | null): Promise<void> {
    requestedId = id;
    error.value = null;
    notFound.value = false;

    if (id === null) {
      meeting.value = null;
      isLoading.value = false;
      return;
    }

    const cached = findCachedMeeting(id);
    if (cached) {
      meeting.value = cached;
      isLoading.value = false;
      return;
    }

    isLoading.value = true;
    meeting.value = null;
    try {
      const loaded = await getMeeting(id);
      if (requestedId === id) {
        meeting.value = loaded;
      }
    } catch (caught) {
      if (requestedId !== id) {
        return;
      }
      if (caught instanceof ApiError && caught.status === 404) {
        notFound.value = true;
      } else {
        error.value =
          caught instanceof ApiError ? caught : new ApiError('network', 'Ошибка загрузки');
      }
    } finally {
      if (requestedId === id) {
        isLoading.value = false;
      }
    }
  }

  watch(meetingId, (id) => void load(id), { immediate: true });

  function open(id: number): void {
    void router.replace({ query: { ...route.query, meeting: String(id) } });
  }

  function close(): void {
    const query = { ...route.query };
    delete query.meeting;
    void router.replace({ query });
  }

  function retry(): void {
    void load(meetingId.value);
  }

  return {
    meetingId,
    meeting,
    isLoading,
    notFound,
    error,
    errorText: computed(() => error.value?.detail ?? null),
    open,
    close,
    retry,
    isOpen: computed(() => meetingId.value !== null),
  };
}
