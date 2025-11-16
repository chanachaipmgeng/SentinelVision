import { ComponentFixture, TestBed } from '@angular/core/testing';

import { HrUserManagementEditComponent } from './hr-user-management-edit.component';

describe('HrUserManagementEditComponent', () => {
  let component: HrUserManagementEditComponent;
  let fixture: ComponentFixture<HrUserManagementEditComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ HrUserManagementEditComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(HrUserManagementEditComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
