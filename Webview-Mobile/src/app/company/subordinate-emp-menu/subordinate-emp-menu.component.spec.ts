import { ComponentFixture, TestBed } from '@angular/core/testing';

import { SubordinateEmpMenuComponent } from './subordinate-emp-menu.component';

describe('SubordinateEmpMenuComponent', () => {
  let component: SubordinateEmpMenuComponent;
  let fixture: ComponentFixture<SubordinateEmpMenuComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ SubordinateEmpMenuComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(SubordinateEmpMenuComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
