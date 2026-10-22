<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue';

import AppIcon from '@/components/ui/AppIcon.vue';
import DropdownList from '@/components/ui/DropdownList.vue';
import { useTickersSearch } from '@/composables/useTickersSearch';
import { useWatchlist } from '@/composables/useWatchlist';
import type { Ticker } from '@/types/ticker';

const props = withDefaults(
  defineProps<{
    modelValue: string;
    autofocus?: boolean;
  }>(),
  { autofocus: false },
);

const emit = defineEmits<{
  'update:modelValue': [value: string];
  add: [ticker: string];
}>();

const query = computed({
  get: () => props.modelValue,
  set: (value: string) => emit('update:modelValue', value),
});

const search = useTickersSearch(query);
const watchlist = useWatchlist();

const root = ref<HTMLElement | null>(null);
const input = ref<HTMLInputElement | null>(null);
const focused = ref(false);
const closed = ref(false);
const activeIndex = ref(-1);

const trimmed = computed(() => props.modelValue.trim());
const showDropdown = computed(() => focused.value && !closed.value && trimmed.value.length > 0);
const showHint = computed(() => trimmed.value.length > 0 && trimmed.value.length < 2);

watch(
  () => search.results.value,
  () => {
    activeIndex.value = -1;
  },
);

watch(
  () => props.modelValue,
  () => {
    closed.value = false;
  },
);

function onInput(event: Event): void {
  const target = event.target as HTMLInputElement;
  query.value = target.value;
}

function onFocus(): void {
  focused.value = true;
  closed.value = false;
}

function onFocusOut(event: FocusEvent): void {
  const next = event.relatedTarget;
  if (next instanceof Node && root.value?.contains(next)) {
    return;
  }
  focused.value = false;
}

function select(ticker: Ticker): void {
  if (watchlist.isWatched(ticker.ticker)) {
    return;
  }
  emit('add', ticker.ticker);
}

function onKeydown(event: KeyboardEvent): void {
  const results = search.results.value;

  if (event.key === 'ArrowDown') {
    if (!results.length) {
      return;
    }
    event.preventDefault();
    activeIndex.value = (activeIndex.value + 1) % results.length;
    return;
  }

  if (event.key === 'ArrowUp') {
    if (!results.length) {
      return;
    }
    event.preventDefault();
    activeIndex.value = activeIndex.value <= 0 ? results.length - 1 : activeIndex.value - 1;
    return;
  }

  if (event.key === 'Enter') {
    const active = results[activeIndex.value];
    const pick = active ?? (results.length === 1 ? results[0] : undefined);
    if (pick) {
      event.preventDefault();
      select(pick);
    }
    return;
  }

  if (event.key === 'Escape') {
    event.stopPropagation();
    closed.value = true;
    activeIndex.value = -1;
  }
}

async function clear(): Promise<void> {
  query.value = '';
  closed.value = true;
  await nextTick();
  input.value?.focus();
}

onMounted(() => {
  if (props.autofocus) {
    input.value?.focus();
    focused.value = true;
  }
});

function focus(): void {
  input.value?.focus();
  focused.value = true;
}

defineExpose({ focus });
</script>

<template>
  <div ref="root" class="search">
    <span class="search__icon" aria-hidden="true">
      <AppIcon name="search" :size="20" />
    </span>
    <input
      ref="input"
      class="search__input"
      type="text"
      placeholder="Найти тикер"
      autocomplete="off"
      role="combobox"
      :aria-expanded="showDropdown"
      aria-controls="ticker-search-results"
      aria-autocomplete="list"
      aria-label="Поиск тикера"
      :value="modelValue"
      :aria-activedescendant="activeIndex >= 0 ? `ticker-option-${activeIndex}` : undefined"
      @input="onInput"
      @focus="onFocus"
      @focusout="onFocusOut"
      @keydown="onKeydown"
    />
    <button
      v-if="modelValue.length > 0"
      class="search__clear"
      type="button"
      aria-label="Очистить поиск"
      @mousedown.prevent
      @click="clear"
    >
      <AppIcon name="close" :size="20" />
    </button>

    <DropdownList :open="showDropdown" id="ticker-search-results">
      <p v-if="showHint" class="search__state">Начните вводить тикер или название</p>
      <p v-else-if="search.isLoading.value" class="search__state">Ищем…</p>
      <p v-else-if="search.errorText.value" class="search__state search__state--error">
        {{ search.errorText.value }}
      </p>
      <p v-else-if="search.results.value.length === 0" class="search__state">
        Тикер не найден
      </p>
      <button
        v-for="(ticker, index) in search.results.value"
        :id="`ticker-option-${index}`"
        :key="ticker.ticker"
        type="button"
        role="option"
        :aria-selected="index === activeIndex"
        :class="['search__item', { 'search__item--active': index === activeIndex }]"
        :disabled="watchlist.isWatched(ticker.ticker) || watchlist.isMutating(ticker.ticker)"
        @mousedown.prevent
        @click="select(ticker)"
      >
        <span class="search__ticker">{{ ticker.ticker }}</span>
        <span class="search__issuer">{{ ticker.short_name }}</span>
        <span class="search__action">
          {{ watchlist.isWatched(ticker.ticker) ? 'Уже отслеживается' : 'Отслеживать' }}
        </span>
      </button>
    </DropdownList>
  </div>
</template>

<style scoped>
.search {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: 0 var(--space-3);
  min-height: 52px;
  background: var(--surface-2);
  border: 1px solid var(--outline-variant);
  border-radius: var(--radius-field);
}

.search:focus-within {
  border-color: var(--primary);
}

.search__icon {
  color: var(--on-surface-muted);
  display: flex;
}

.search__input {
  flex: 1;
  min-width: 0;
  border: 0;
  background: transparent;
  color: var(--on-surface);
  padding: var(--space-3) 0;
  font-size: var(--font-size-body-lg);
  line-height: var(--line-height-body-lg);
}

.search__input:focus-visible {
  outline: none;
}

.search__input::placeholder {
  color: var(--on-surface-muted);
}

.search__clear {
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: var(--on-surface-muted);
}

.search__clear:hover {
  background: color-mix(in srgb, var(--on-surface) 8%, transparent);
  color: var(--on-surface);
}

.search__state {
  padding: var(--space-3);
  color: var(--on-surface-muted);
}

.search__state--error {
  color: var(--danger);
}

.search__item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: inherit;
  text-align: left;
}

.search__item:hover:not(:disabled),
.search__item--active {
  background: color-mix(in srgb, var(--on-surface) 8%, transparent);
}

.search__item:disabled {
  opacity: 0.6;
  cursor: default;
}

.search__ticker {
  font-weight: 600;
  letter-spacing: 0.02em;
}

.search__issuer {
  color: var(--on-surface-variant);
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.search__action {
  color: var(--primary);
  font-size: var(--font-size-label-md);
  white-space: nowrap;
}

.search__item:disabled .search__action {
  color: var(--on-surface-muted);
}
</style>
