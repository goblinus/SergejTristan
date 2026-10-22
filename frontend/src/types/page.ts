/** Конверт пагинации всех списковых эндпоинтов. */
export interface Page<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
}
