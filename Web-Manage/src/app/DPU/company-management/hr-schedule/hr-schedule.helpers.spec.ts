import {
  defaultNewLeave,
  defaultNewShift,
  holidayImportFormat,
  holidaySourceLabel,
  isHrScheduleTab,
  parseLeaveList,
  retentionFromPdpaSummary,
} from './hr-schedule.helpers';

describe('hr-schedule.helpers', () => {
  it('holidaySourceLabel maps known sources', () => {
    expect(holidaySourceLabel('CSV')).toBe('CSV');
    expect(holidaySourceLabel('ICAL')).toBe('iCal');
    expect(holidaySourceLabel('THAI_PRESET')).toBe('ราชการไทย');
    expect(holidaySourceLabel(null)).toBe('กำหนดเอง');
  });

  it('holidayImportFormat detects ics vs csv', () => {
    expect(holidayImportFormat('holidays.ics')).toBe('ical');
    expect(holidayImportFormat('holidays.ICAL')).toBe('ical');
    expect(holidayImportFormat('holidays.csv')).toBe('csv');
  });

  it('default shapes have expected fields', () => {
    expect(defaultNewShift().startTime).toBe('09:00');
    expect(defaultNewLeave().leaveType).toBe('ANNUAL');
  });

  it('parseLeaveList accepts array or items wrapper', () => {
    expect(parseLeaveList([{ leaveId: '1' }])).toEqual([{ leaveId: '1' }]);
    expect(parseLeaveList({ items: [{ leaveId: '2' }] })).toEqual([{ leaveId: '2' }]);
    expect(parseLeaveList(null)).toEqual([]);
  });

  it('retentionFromPdpaSummary merges imageRetentionDays alias', () => {
    const result = retentionFromPdpaSummary(
      { imageRetentionDays: 30, tempRetentionHours: 12, videoClipDays: 14 },
      {
        biometricDays: 90,
        punchPhotoDays: 90,
        incidentSnapshotDays: 90,
        videoClipDays: 30,
        tempHours: 24,
      },
    );
    expect(result.punchPhotoDays).toBe(30);
    expect(result.tempHours).toBe(12);
    expect(result.videoClipDays).toBe(14);
  });

  it('isHrScheduleTab validates tab ids', () => {
    expect(isHrScheduleTab('shifts')).toBe(true);
    expect(isHrScheduleTab('nope')).toBe(false);
  });
});
