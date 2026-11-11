import { CommonModule } from '@angular/common';
import { Component, OnInit, ViewEncapsulation } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { SharedModule } from '../../../shared/shared.module';
import { speakText, unlockSpeech } from '../../../shared/utils/tts';
import {
  DEFAULT_TTS_TEMPLATES,
  TtsSettings,
  TtsTemplateKey,
  buildSpeechText,
  resolveTtsSettings,
} from '../../../shared/utils/tts-templates';
import { SystemSettingService } from '../../services/system-setting.service';
import swal from 'sweetalert';

@Component({
    selector: 'app-system-setting',
    imports: [SharedModule, CommonModule, FormsModule],
    templateUrl: './system-setting.component.html',
    styleUrl: './system-setting.component.css',
    encapsulation: ViewEncapsulation.None
})
export class SystemSettingComponent implements OnInit {
  loading = false;
  saving = false;
  ttsForm: TtsSettings = resolveTtsSettings(null);

  readonly ttsTemplateFields: { key: TtsTemplateKey; label: string }[] = [
    { key: 'checkInSuccess', label: 'ลงเวลาสำเร็จ' },
    { key: 'checkInWarning', label: 'ลงเวลานอกพื้นที่ (Warning)' },
    { key: 'checkInDuplicate', label: 'ลงเวลาซ้ำ' },
    { key: 'enrollSuccess', label: 'เก็บหน้าสำเร็จ' },
    { key: 'enrollFailed', label: 'เก็บหน้าไม่สำเร็จ' },
  ];

  constructor(private systemSettingService: SystemSettingService) {}

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading = true;
    this.systemSettingService.getTtsSettings().subscribe({
      next: (settings) => {
        this.ttsForm = settings;
        this.loading = false;
      },
      error: () => {
        this.loading = false;
        this.ttsForm = resolveTtsSettings(null);
        swal('Error', 'โหลดการตั้งค่าเสียงพูดไม่สำเร็จ', 'error');
      },
    });
  }

  previewTts(key: TtsTemplateKey): void {
    unlockSpeech();
    const settings = resolveTtsSettings({
      enabled: true,
      lang: this.ttsForm.lang,
      rate: this.ttsForm.rate,
      pitch: this.ttsForm.pitch,
      templates: this.ttsForm.templates,
    });
    const text = buildSpeechText(settings, key, {
      name: 'ชนะชัย ใจดี',
      firstName: 'ชนะชัย',
      employeeId: 'DPU-001',
    });
    if (text) {
      speakText(text, {
        lang: settings.lang,
        rate: settings.rate,
        pitch: settings.pitch,
      });
    }
  }

  resetTtsDefaults(): void {
    this.ttsForm = {
      ...resolveTtsSettings(null),
      enabled: this.ttsForm.enabled,
      rate: this.ttsForm.rate,
      pitch: this.ttsForm.pitch,
      templates: { ...DEFAULT_TTS_TEMPLATES },
    };
  }

  save(): void {
    const payload = resolveTtsSettings({
      enabled: this.ttsForm.enabled,
      lang: this.ttsForm.lang || 'th-TH',
      rate: this.ttsForm.rate,
      pitch: this.ttsForm.pitch,
      templates: this.ttsForm.templates,
    });
    swal({
      title: 'บันทึกการตั้งค่าเสียงพูด?',
      text: 'ใช้ร่วมกันทุกบริษัท',
      icon: 'warning',
      buttons: ['ยกเลิก', 'บันทึก'],
    }).then((ok: unknown) => {
      if (!ok) return;
      this.saving = true;
      this.systemSettingService.updateTtsSettings(payload).subscribe({
        next: (saved) => {
          this.ttsForm = saved;
          this.saving = false;
          swal('สำเร็จ', 'บันทึกการตั้งค่าเสียงพูดแล้ว', 'success');
        },
        error: (err) => {
          this.saving = false;
          const detail = err?.error?.detail;
          swal(
            'บันทึกไม่สำเร็จ',
            typeof detail === 'string' ? detail : 'อัปเดตไม่สำเร็จ',
            'error',
          );
        },
      });
    });
  }
}
