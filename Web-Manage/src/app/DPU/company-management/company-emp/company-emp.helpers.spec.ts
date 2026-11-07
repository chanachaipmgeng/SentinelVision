import {
  clampPageIndex,
  filterEmployees,
  formatApiError,
  isExcelImportFile,
  lerpBox,
  pageSizeForView,
  slicePage,
  totalPages,
  translateApiMessage,
  validateEmployeeForm,
} from './company-emp.helpers';
import { EmployeeModel } from '../../models/employee.model';

function emp(partial: Partial<EmployeeModel> & { email?: string; firstName?: string }): EmployeeModel {
  const m = new EmployeeModel();
  m.company_employeeId = partial.company_employeeId || 'ce-1';
  m.employeeId = partial.employeeId || 'E001';
  (m as any).member = {
    email: partial.email || 'a@b.com',
    firstName: partial.firstName || 'An',
    lastName: 'Bee',
    getPicture: () => '',
  };
  (m as any).getFullname = () => `${(m as any).member.firstName} ${(m as any).member.lastName}`;
  (m as any).getType = () => 'monthly';
  (m as any).getRole = () => 'emp';
  (m as any).position = { getName: () => 'Dev', thName: 'Dev', positionId: 'p1' };
  (m as any).department = { getName: () => 'IT', thName: 'IT', departmentId: 'd1' };
  m.empType = 1;
  return m;
}

describe('company-emp.helpers', () => {
  it('filterEmployees matches name/email/code', () => {
    const list = [emp({ firstName: 'Somchai', email: 'som@co.th', employeeId: 'EMP9' })];
    expect(filterEmployees(list, 'somchai').length).toBe(1);
    expect(filterEmployees(list, 'emp9').length).toBe(1);
    expect(filterEmployees(list, 'zzz').length).toBe(0);
  });

  it('paging helpers', () => {
    expect(pageSizeForView('cards')).toBe(9);
    expect(pageSizeForView('table')).toBe(10);
    expect(totalPages(25, 10)).toBe(3);
    expect(clampPageIndex(9, 25, 10)).toBe(2);
    expect(slicePage([1, 2, 3, 4, 5], 1, 2)).toEqual([3, 4]);
  });

  it('validateEmployeeForm requires core fields', () => {
    const bad = new EmployeeModel();
    expect(validateEmployeeForm(bad)).toContain('อีเมล');
    const good = emp({});
    expect(validateEmployeeForm(good)).toBeNull();
  });

  it('translateApiMessage / formatApiError', () => {
    expect(translateApiMessage('value is not a valid email address')).toContain('อีเมล');
    expect(formatApiError({ error: { detail: 'already exists' } })).toContain('อีเมลนี้');
    expect(isExcelImportFile('a.xlsx')).toBe(true);
    expect(isExcelImportFile('a.csv')).toBe(false);
  });

  it('lerpBox interpolates', () => {
    const out = lerpBox({ x: 0, y: 0, width: 10, height: 10 }, { x: 10, y: 10, width: 20, height: 20 }, 0.5);
    expect(out.x).toBe(5);
    expect(out.width).toBe(15);
  });
});
