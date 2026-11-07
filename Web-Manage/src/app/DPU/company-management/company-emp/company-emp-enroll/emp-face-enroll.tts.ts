import { speakText } from '../../../../shared/utils/tts';
import {
  TtsSettings,
  buildSpeechText,
} from '../../../../shared/utils/tts-templates';
import { EmployeeModel } from '../../../models/employee.model';

export function enrollSpeechVars(selectModel: EmployeeModel | null | undefined): {
  name: string;
  firstName: string;
  employeeId: string;
} {
  const member = selectModel?.member;
  const name =
    (typeof selectModel?.getFullname === 'function' ? selectModel.getFullname() : '')?.trim() ||
    `${member?.firstName || ''} ${member?.lastName || ''}`.trim() ||
    'พนักงาน';
  return {
    name,
    firstName: (member?.firstName || name.split(/\s+/)[0] || '').trim(),
    employeeId: selectModel?.employeeId || '',
  };
}

export function speakEnroll(
  ttsSettings: TtsSettings,
  selectModel: EmployeeModel | null | undefined,
  success: boolean,
): void {
  const text = buildSpeechText(
    ttsSettings,
    success ? 'enrollSuccess' : 'enrollFailed',
    enrollSpeechVars(selectModel),
  );
  if (!text) return;
  speakText(text, {
    lang: ttsSettings.lang,
    rate: ttsSettings.rate,
    pitch: ttsSettings.pitch,
    cancelPrevious: true,
  });
}
