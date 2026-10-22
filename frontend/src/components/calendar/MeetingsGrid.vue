<script setup lang="ts">
import type { MeetingCardModel } from '@/composables/useCalendar';

import MeetingCard from './MeetingCard.vue';

defineProps<{
  cards: MeetingCardModel[];
}>();

defineEmits<{
  open: [id: number];
}>();
</script>

<template>
  <div class="grid">
    <MeetingCard
      v-for="card in cards"
      :key="card.meeting.id"
      :card="card"
      @open="$emit('open', $event)"
    />
  </div>
</template>
