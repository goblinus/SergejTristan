<script setup lang="ts">
import { computed, ref, watch } from 'vue';

import AppIcon from '@/components/ui/AppIcon.vue';

const props = withDefaults(
  defineProps<{
    logoUrl: string | null;
    ticker: string;
    name: string;
    size?: 32 | 36;
    watched?: boolean;
  }>(),
  { size: 32, watched: false },
);

const failed = ref(false);

watch(
  () => props.logoUrl,
  () => {
    failed.value = false;
  },
);

const showLogo = computed(() => Boolean(props.logoUrl) && !failed.value);
const monogram = computed(() => props.ticker.slice(0, 1).toUpperCase());
const dimensions = computed(() => ({ width: `${props.size}px`, height: `${props.size}px` }));
</script>

<template>
  <div class="identity">
    <img
      v-if="showLogo"
      :src="logoUrl ?? ''"
      alt=""
      :style="dimensions"
      class="identity__logo"
      @error="failed = true"
    />
    <span
      v-else
      class="identity__monogram"
      :style="{ ...dimensions, fontSize: size === 36 ? '15px' : '13px' }"
      aria-hidden="true"
    >
      {{ monogram }}
    </span>
    <div class="identity__text">
      <span class="identity__ticker">{{ ticker }}</span>
      <span class="identity__name">{{ name }}</span>
    </div>
    <AppIcon v-if="watched" name="star" :size="16" class="identity__star" />
  </div>
</template>

<style scoped>
.identity {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  min-width: 0;
}

.identity__logo,
.identity__monogram {
  border-radius: 8px;
  background: var(--surface-3);
  object-fit: contain;
  flex: none;
}

.identity__monogram {
  display: grid;
  place-items: center;
  color: var(--on-surface-variant);
  font-weight: 700;
  line-height: 1;
}

.identity__text {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
  min-width: 0;
}

.identity__ticker {
  font-size: var(--font-size-body-lg);
  line-height: var(--line-height-body-lg);
  font-weight: 600;
  letter-spacing: 0.02em;
}

.identity__name {
  color: var(--on-surface-variant);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.identity__star {
  color: var(--primary);
  margin-left: auto;
}
</style>
