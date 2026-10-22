<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';

import CompanyIdentity from '@/components/company/CompanyIdentity.vue';
import DsiBadge from '@/components/dividend/DsiBadge.vue';
import AppIcon from '@/components/ui/AppIcon.vue';
import Skeleton from '@/components/ui/Skeleton.vue';
import { useWatchlist } from '@/composables/useWatchlist';
import type { Meeting } from '@/types/meeting';
import { formatDate } from '@/utils/date';
import { formatMoney, formatPercent, formatPeriod } from '@/utils/formatDividend';

const props = defineProps<{
  meeting: Meeting | null;
  isLoading: boolean;
  notFound: boolean;
  errorText: string | null;
}>();

const emit = defineEmits<{
  close: [];
  retry: [];
}>();

const watchlist = useWatchlist();
const closeButton = ref<HTMLButtonElement | null>(null);

const watched = computed(() =>
  props.meeting ? watchlist.isWatched(props.meeting.ticker) : false,
);
const isMutating = computed(() =>
  props.meeting ? watchlist.isMutating(props.meeting.ticker) : false,
);

const cutoffLabel = computed(() => {
  const meeting = props.meeting;
  if (!meeting) {
    return '—';
  }
  return meeting.record_date ? formatDate(meeting.record_date.record_date) : 'будет объявлена позже';
});

function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') {
    emit('close');
  }
}

onMounted(() => {
  document.addEventListener('keydown', onKeydown);
  document.body.classList.add('modal-open');
  closeButton.value?.focus();
});

onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKeydown);
  document.body.classList.remove('modal-open');
});

async function watch(): Promise<void> {
  if (props.meeting) {
    await watchlist.add(props.meeting.ticker);
  }
}
</script>

<template>
  <Teleport to="body">
    <div class="overlay" @click.self="$emit('close')">
      <div
        class="dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="meetingDialogTitle"
      >
        <div class="dialog__head">
          <h2 id="meetingDialogTitle" class="visually-hidden">
            Детали собрания{{ meeting ? `: ${meeting.ticker}` : '' }}
          </h2>
          <CompanyIdentity
            v-if="meeting"
            :logo-url="meeting.logo_url"
            :ticker="meeting.ticker"
            :name="meeting.short_name"
            :size="36"
          />
          <h2 v-else class="dialog__title">Детали собрания</h2>
          <button
            ref="closeButton"
            class="dialog__close"
            type="button"
            aria-label="Закрыть"
            @click="$emit('close')"
          >
            <AppIcon name="close" :size="24" />
          </button>
        </div>

        <div v-if="isLoading" class="dialog__body">
          <Skeleton variant="fields" :count="3" />
        </div>

        <div v-else-if="notFound" class="dialog__body dialog__message">
          <p class="dialog__message-title">Собрание не найдено</p>
          <p class="dialog__message-text">Возможно, ссылка устарела или собрание удалено.</p>
        </div>

        <div v-else-if="errorText" class="dialog__body dialog__message">
          <p class="dialog__message-title">Не удалось загрузить собрание</p>
          <p class="dialog__message-text">{{ errorText }}</p>
          <button type="button" class="dialog__link-btn" @click="$emit('retry')">
            Повторить
          </button>
        </div>

        <template v-else-if="meeting">
          <dl class="dialog__rows">
            <div>
              <dt>Дата собрания</dt>
              <dd class="tabular">{{ formatDate(meeting.meeting_date) }}</dd>
            </div>
            <div>
              <dt>Дата отсечки (реестр)</dt>
              <dd class="tabular">{{ cutoffLabel }}</dd>
            </div>
            <div>
              <dt>Вопрос о дивидендах</dt>
              <dd>{{ meeting.description ?? '—' }}</dd>
            </div>
            <div>
              <dt>Выплаты за период</dt>
              <dd>{{ formatPeriod(meeting.dividend?.period ?? null) }}</dd>
            </div>
            <div>
              <dt>Выплата на акцию</dt>
              <dd class="tabular">{{ formatMoney(meeting.dividend?.amount_per_share ?? null) }}</dd>
            </div>
            <div>
              <dt>Доходность</dt>
              <dd class="tabular">{{ formatPercent(meeting.dividend?.yield_percent ?? null) }}</dd>
            </div>
            <div>
              <dt>Статус сторожка</dt>
              <dd>
                <span :class="['status', { 'status--on': watched }]">
                  {{ watched ? 'в сторожках' : 'нет' }}
                </span>
              </dd>
            </div>
            <div v-if="meeting.source_url">
              <dt>Источник</dt>
              <dd>
                <a
                  class="dialog__source"
                  :href="meeting.source_url"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  раскрытие эмитента
                  <AppIcon name="open_in_new" :size="16" />
                </a>
              </dd>
            </div>
            <div>
              <dt>DSI</dt>
              <dd><DsiBadge :value="meeting.dsi" /></dd>
            </div>
          </dl>

          <div class="dialog__actions">
            <button
              v-if="!watched"
              type="button"
              class="btn-primary"
              :disabled="isMutating"
              @click="watch"
            >
              Отслеживать этот тикер
            </button>
            <button v-else type="button" class="btn-primary" disabled>Сторожок установлен</button>
            <button type="button" class="btn-ghost" @click="$emit('close')">Закрыть</button>
          </div>
        </template>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  z-index: var(--z-modal);
  display: grid;
  place-items: center;
  padding: var(--space-4);
  background: rgba(0, 0, 0, 0.55);
}

.dialog {
  width: min(560px, 100%);
  max-height: min(86vh, 720px);
  overflow-y: auto;
  background: var(--surface-3);
  border: 1px solid var(--outline-variant);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-modal);
  padding: var(--space-5);
}

.dialog__head {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--outline-variant);
}

.dialog__title {
  font-size: var(--font-size-title-lg);
  line-height: var(--line-height-title-lg);
  font-weight: 600;
}

.dialog__close {
  margin-left: auto;
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: var(--on-surface-variant);
}

.dialog__close:hover {
  background: color-mix(in srgb, var(--on-surface) 8%, transparent);
  color: var(--on-surface);
}

.dialog__body {
  padding-top: var(--space-4);
}

.dialog__rows {
  display: grid;
  gap: var(--space-1);
  padding: var(--space-4) 0;
}

.dialog__rows > div {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.2fr);
  gap: var(--space-3);
  padding: var(--space-2) 0;
  border-bottom: 1px solid var(--outline-variant);
}

.dialog__rows > div:last-child {
  border-bottom: 0;
}

.dialog__rows dt {
  color: var(--on-surface-muted);
}

.dialog__rows dd {
  color: var(--on-surface);
}

.status {
  display: inline-flex;
  padding: 2px 10px;
  border-radius: var(--radius-chip);
  background: var(--neutral-chip);
  color: var(--on-surface-variant);
  font-size: var(--font-size-label-md);
}

.status--on {
  background: var(--primary-container);
  color: var(--on-primary-container);
}

.dialog__source {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.dialog__actions {
  display: flex;
  gap: var(--space-3);
  justify-content: flex-end;
  padding-top: var(--space-4);
}

.btn-primary,
.btn-ghost {
  border: 0;
  border-radius: var(--radius-button);
  min-height: 40px;
  padding: 0 var(--space-5);
  font-weight: 500;
}

.btn-primary {
  background: var(--primary);
  color: var(--on-primary);
}

.btn-primary:disabled {
  opacity: 0.38;
  cursor: default;
}

.btn-ghost {
  background: transparent;
  color: var(--primary);
}

.btn-ghost:hover {
  background: color-mix(in srgb, var(--on-surface) 8%, transparent);
}

.dialog__message {
  display: grid;
  gap: var(--space-2);
  padding: var(--space-6) 0;
}

.dialog__message-title {
  font-weight: 600;
}

.dialog__message-text {
  color: var(--on-surface-variant);
}

.dialog__link-btn {
  justify-self: start;
  border: 0;
  background: transparent;
  color: var(--primary);
  padding: var(--space-1) 0;
}

@media (max-width: 640px) {
  .overlay {
    place-items: end center;
    padding: 0;
  }

  .dialog {
    width: 100%;
    max-height: 90vh;
    border-bottom-left-radius: 0;
    border-bottom-right-radius: 0;
    background: var(--surface-4);
  }

  .dialog__rows > div {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  }

  .dialog__actions {
    flex-direction: column-reverse;
  }

  .btn-primary,
  .btn-ghost {
    width: 100%;
  }
}
</style>
