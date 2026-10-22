import { onBeforeUnmount, ref, type Ref } from 'vue';

/** Реактивный media query; по умолчанию для мобильной компоновки ≤640px. */
export function useMediaQuery(query = '(max-width: 640px)'): Ref<boolean> {
  const matches = ref(false);

  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
    return matches;
  }

  const mql = window.matchMedia(query);
  matches.value = mql.matches;

  const onChange = (event: MediaQueryListEvent): void => {
    matches.value = event.matches;
  };

  mql.addEventListener('change', onChange);
  onBeforeUnmount(() => mql.removeEventListener('change', onChange));

  return matches;
}
