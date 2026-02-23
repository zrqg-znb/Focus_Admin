import { requestClient } from '#/api/request';

export type MessagePriority = 'high' | 'low' | 'normal' | 'urgent';
export type MessageType = 'announcement' | 'internal' | 'system';

export interface UserMessage {
  id: string;
  title: string;
  content: string;
  message_type: MessageType;
  priority: MessagePriority;
  is_read: boolean;
  read_at?: null | string;
  link?: null | string;
  extra_data?: null | Record<string, any>;
  sender_id?: null | string;
  sender_name?: null | string;
  sender_avatar?: null | string;
  announcement_id?: null | string;
  sys_create_datetime?: null | string;
  sys_update_datetime?: null | string;
}

export interface UserMessageListParams {
  is_read?: boolean;
  keyword?: string;
  message_type?: MessageType;
  page?: number;
  pageSize?: number;
}

export interface AnnouncementItem {
  id: string;
  title: string;
  content: string;
  priority: MessagePriority;
  status: number;
  publish_at?: null | string;
  expire_at?: null | string;
  sys_create_datetime?: null | string;
  sys_update_datetime?: null | string;
}

export interface AnnouncementListParams {
  page?: number;
  pageSize?: number;
  status?: number;
  title?: string;
}

export interface AnnouncementPayload {
  title: string;
  content: string;
  priority?: MessagePriority;
  expire_at?: null | string;
}

export interface InternalMessagePayload {
  receiver_ids: string[];
  title: string;
  content: string;
  priority?: MessagePriority;
  link?: null | string;
  extra_data?: Record<string, any>;
}

export interface MessageActionResult {
  count?: number;
  msg: string;
}

export interface PaginatedResult<T> {
  items: T[];
  total: number;
}

export async function getInboxMessageListApi(params?: UserMessageListParams) {
  return requestClient.get<PaginatedResult<UserMessage>>('/api/core/message/inbox', {
    params,
  });
}

export async function getUnreadMessageCountApi() {
  return requestClient.get<{ unread_count: number }>('/api/core/message/unread/count');
}

export async function markMessageReadApi(messageId: string) {
  return requestClient.post<MessageActionResult>(
    `/api/core/message/${messageId}/read`,
  );
}

export async function markAllMessagesReadApi() {
  return requestClient.post<MessageActionResult>('/api/core/message/read/all');
}

export async function deleteInboxMessageApi(messageId: string) {
  return requestClient.delete<MessageActionResult>(`/api/core/message/${messageId}`);
}

export async function clearInboxMessageApi() {
  return requestClient.delete<MessageActionResult>('/api/core/message/clear/all');
}

export async function sendInternalMessageApi(data: InternalMessagePayload) {
  return requestClient.post<MessageActionResult>('/api/core/message/send', data);
}

export async function getAnnouncementListApi(params?: AnnouncementListParams) {
  return requestClient.get<PaginatedResult<AnnouncementItem>>('/api/core/announcement', {
    params,
  });
}

export async function createAnnouncementApi(data: AnnouncementPayload) {
  return requestClient.post<AnnouncementItem>('/api/core/announcement', data);
}

export async function updateAnnouncementApi(
  announcementId: string,
  data: Partial<AnnouncementPayload>,
) {
  return requestClient.put<AnnouncementItem>(
    `/api/core/announcement/${announcementId}`,
    data,
  );
}

export async function publishAnnouncementApi(announcementId: string) {
  return requestClient.post<MessageActionResult>(
    `/api/core/announcement/${announcementId}/publish`,
  );
}

export async function revokeAnnouncementApi(announcementId: string) {
  return requestClient.post<MessageActionResult>(
    `/api/core/announcement/${announcementId}/revoke`,
  );
}

export async function deleteAnnouncementApi(announcementId: string) {
  return requestClient.delete<MessageActionResult>(
    `/api/core/announcement/${announcementId}`,
  );
}
