import { request } from '@/api/http';
import type { Meeting, MeetingsQuery } from '@/types/meeting';
import type { Page } from '@/types/page';

export function getMeetings(params: MeetingsQuery = {}): Promise<Page<Meeting>> {
  return request<Page<Meeting>>('GET', '/v1/meetings', { params: { ...params } });
}

export function getMeeting(id: number): Promise<Meeting> {
  return request<Meeting>('GET', `/v1/meetings/${id}`);
}
