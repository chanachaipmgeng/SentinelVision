import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { resolveTtsSettings, TtsSettings } from '../../shared/utils/tts-templates';

@Injectable({
  providedIn: 'root',
})
export class SystemSettingService {
  private readonly ttsUrl = '/system/tts-settings';

  constructor(private http: HttpClient) {}

  getTtsSettings(): Observable<TtsSettings> {
    return this.http
      .get<Record<string, unknown>>(this.ttsUrl)
      .pipe(map((raw) => resolveTtsSettings(raw)));
  }

  updateTtsSettings(settings: TtsSettings): Observable<TtsSettings> {
    return this.http
      .put<Record<string, unknown>>(this.ttsUrl, settings)
      .pipe(map((raw) => resolveTtsSettings(raw)));
  }
}
