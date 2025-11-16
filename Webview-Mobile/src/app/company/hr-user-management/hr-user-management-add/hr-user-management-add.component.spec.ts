import { ComponentFixture, TestBed } from '@angular/core/testing';

import { HrUserManagementAddComponent } from './hr-user-management-add.component';

describe('HrUserManagementAddComponent', () => {
  let component: HrUserManagementAddComponent;
  let fixture: ComponentFixture<HrUserManagementAddComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ HrUserManagementAddComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(HrUserManagementAddComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
