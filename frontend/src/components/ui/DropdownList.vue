<script setup lang="ts">
defineProps<{
  open: boolean;
  labelledBy?: string;
  id?: string;
}>();
</script>

<template>
  <div v-show="open" :id="id" class="dropdown" role="listbox" :aria-labelledby="labelledBy">
    <slot />
  </div>
</template>

<style scoped>
.dropdown {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  z-index: var(--z-modal);
  max-height: 320px;
  overflow-y: auto;
  padding: var(--space-1);
  border-radius: var(--radius-card);
  background: var(--surface-3);
  border: 1px solid var(--outline-variant);
  box-shadow: var(--shadow-modal);
}
</style>
