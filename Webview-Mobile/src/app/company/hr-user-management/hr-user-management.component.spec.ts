import { ComponentFixture, TestBed } from '@angular/core/testing';

import { HrUserManagementComponent } from './hr-user-management.component';

describe('HrUserManagementComponent', () => {
  let component: HrUserManagementComponent;
  let fixture: ComponentFixture<HrUserManagementComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ HrUserManagementComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(HrUserManagementComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
