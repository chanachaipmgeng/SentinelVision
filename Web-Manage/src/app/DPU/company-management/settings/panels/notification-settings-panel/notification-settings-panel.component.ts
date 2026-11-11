import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, Input, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { TranslateModule } from '@ngx-translate/core';
import { TokenService } from '../../../../../shared/services/token.service';

type NotifyStatus = 'idle' | 'saved' | 'tested' | 'error';

interface CompanyNotifySettings {
  email?: string;
  hasLineToken?: boolean;
  telegramChatId?: string;
  hasTelegramBotToken?: boolean;
  hasDiscordWebhookUrl?: boolean;
}

/** Company notification channels (email / LINE / Telegram / Discord) — settings hub. */
@Component({
    selector: 'app-notification-settings-panel',
    imports: [CommonModule, FormsModule, TranslateModule],
    templateUrl: './notification-settings-panel.component.html'
})
export class NotificationSettingsPanelComponent implements OnInit {
  /** Override the selected company (defaults to TokenService selection). */
  @Input() companyId = '';

  email = '';
  lineToken = '';
  hasLineToken = false;
  telegramBotToken = '';
  telegramChatId = '';
  hasTelegramBotToken = false;
  discordWebhookUrl = '';
  hasDiscordWebhookUrl = false;
  loading = false;
  busy = false;
  status: NotifyStatus = 'idle';

  constructor(private http: HttpClient, private token: TokenService) {}

  ngOnInit(): void {
    if (!this.companyId) {
      this.companyId = this.token.getSelectCompany()?.companyId || '';
    }
    if (!this.companyId) return;
    this.loading = true;
    this.http.get<CompanyNotifySettings>(`/notifications/company/${this.companyId}/settings`).subscribe({
      next: (s) => {
        this.email = s?.email || '';
        this.lineToken = '';
        this.hasLineToken = !!s?.hasLineToken;
        this.telegramBotToken = '';
        this.telegramChatId = s?.telegramChatId || '';
        this.hasTelegramBotToken = !!s?.hasTelegramBotToken;
        this.discordWebhookUrl = '';
        this.hasDiscordWebhookUrl = !!s?.hasDiscordWebhookUrl;
        this.loading = false;
      },
      error: () => (this.loading = false),
    });
  }

  saveNotify(): void {
    if (!this.companyId || this.busy) return;
    this.busy = true;
    const body: Record<string, string> = {
      email: this.email,
      telegramChatId: this.telegramChatId,
    };
    // Blank secret inputs mean "keep existing" on the API.
    if (this.lineToken.trim()) body['lineToken'] = this.lineToken.trim();
    if (this.telegramBotToken.trim()) body['telegramBotToken'] = this.telegramBotToken.trim();
    if (this.discordWebhookUrl.trim()) body['discordWebhookUrl'] = this.discordWebhookUrl.trim();
    this.http.put<CompanyNotifySettings>(`/notifications/company/${this.companyId}/settings`, body).subscribe({
      next: (s) => {
        this.lineToken = '';
        this.telegramBotToken = '';
        this.discordWebhookUrl = '';
        this.hasLineToken = !!s?.hasLineToken;
        this.hasTelegramBotToken = !!s?.hasTelegramBotToken;
        this.hasDiscordWebhookUrl = !!s?.hasDiscordWebhookUrl;
        this.telegramChatId = s?.telegramChatId || this.telegramChatId;
        this.done('saved');
      },
      error: () => this.done('error'),
    });
  }

  testNotify(): void {
    if (!this.companyId || this.busy) return;
    this.busy = true;
    this.http.post(`/notifications/company/${this.companyId}/test`, {}).subscribe({
      next: () => this.done('tested'),
      error: () => this.done('error'),
    });
  }

  private done(status: NotifyStatus): void {
    this.busy = false;
    this.status = status;
  }
}
