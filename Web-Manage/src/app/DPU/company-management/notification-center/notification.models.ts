export interface InboxNotification {
  id?: string;
  event?: string;
  title?: string;
  body?: string;
  createdAt?: string | Date;
  readAt?: string | Date | null;
  [key: string]: unknown;
}

export interface DeadLetterRow {
  id?: string;
  event?: string;
  channel?: string;
  attempts?: number;
  lastError?: string;
  createdAt?: string | Date;
  deadLetteredAt?: string | Date;
  [key: string]: unknown;
}

export interface NotificationPrefs {
  channelEmail: boolean;
  channelLine: boolean;
  channelInApp: boolean;
  lineUserId: string;
  mutedEvents: string[];
  locale: string;
}

export interface NotificationTemplateRow {
  eventKey?: string;
  locale?: string;
  channel?: string;
  subject?: string;
  bodyTemplate?: string;
}

export interface NotificationTemplatesView {
  builtins: NotificationTemplateRow[];
  custom: NotificationTemplateRow[];
  i18nKeys: Record<string, string>;
}
