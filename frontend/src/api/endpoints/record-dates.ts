import { request } from '@/api/http';
import type { Page } from '@/types/page';
import type { RecordDate, RecordDatesQuery } from '@/types/record-date';

export function getRecordDates(params: RecordDatesQuery = {}): Promise<Page<RecordDate>> {
  return request<Page<RecordDate>>('GET', '/v1/record-dates', { params: { ...params } });
}
