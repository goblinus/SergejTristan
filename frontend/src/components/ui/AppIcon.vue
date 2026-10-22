<script setup lang="ts">
import { computed } from 'vue';

import { ICON_PATHS, type IconName } from './iconPaths';

const props = withDefaults(
  defineProps<{
    name: IconName;
    size?: number;
  }>(),
  { size: 24 },
);

const path = computed(() => ICON_PATHS[props.name]);
</script>

<template>
  <svg
    class="icon"
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    aria-hidden="true"
    focusable="false"
  >
    <path fill="currentColor" :d="path" />
  </svg>
</template>

<style scoped>
.icon {
  display: block;
  flex: none;
}
</style>
