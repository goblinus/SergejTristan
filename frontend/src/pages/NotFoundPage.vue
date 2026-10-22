<script setup lang="ts">
import StateBanner from '@/components/ui/StateBanner.vue';
import { useRouter } from 'vue-router';

const router = useRouter();

function goCalendar(): void {
  void router.push({ name: 'calendar' });
}
</script>

<template>
  <section class="page not-found">
    <StateBanner
      variant="empty"
      title="Страница не найдена"
      text="Такой страницы нет или она была перемещена."
      action-label="Перейти к календарю"
      @action="goCalendar"
    />
  </section>
</template>

<style scoped>
.not-found {
  display: grid;
  place-items: center;
  min-height: 50vh;
}
</style>
