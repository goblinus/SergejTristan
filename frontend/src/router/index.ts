import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router';

import CalendarPage from '@/pages/CalendarPage.vue';

const routes: RouteRecordRaw[] = [
  { path: '/', redirect: { name: 'calendar' } },
  { path: '/calendar', name: 'calendar', component: CalendarPage },
  {
    path: '/me',
    name: 'me',
    component: () => import('@/pages/WatchlistPage.vue'),
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/pages/NotFoundPage.vue'),
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, _from, savedPosition) {
    if (savedPosition) {
      return savedPosition;
    }
    if (to.query.meeting !== undefined && to.name === 'calendar') {
      return false;
    }
    return { top: 0 };
  },
});

/** Валидация query: нечисловой ?meeting и пустой ?ticker удаляются. */
router.beforeEach((to) => {
  if (to.name === 'calendar' && to.query.meeting !== undefined) {
    const raw = Array.isArray(to.query.meeting) ? to.query.meeting[0] : to.query.meeting;
    const parsed = Number(raw);
    if (!Number.isInteger(parsed) || parsed <= 0) {
      const query = { ...to.query };
      delete query.meeting;
      return { name: 'calendar', query, replace: true };
    }
  }

  if (to.name === 'me' && to.query.ticker !== undefined) {
    const raw = Array.isArray(to.query.ticker) ? to.query.ticker[0] : to.query.ticker;
    const normalized = (raw ?? '').trim().toUpperCase();
    if (!normalized) {
      const query = { ...to.query };
      delete query.ticker;
      return { name: 'me', query, replace: true };
    }
    if (normalized !== raw) {
      return { name: 'me', query: { ...to.query, ticker: normalized }, replace: true };
    }
  }

  return true;
});

export default router;
