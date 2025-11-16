import { ComponentFixture, TestBed } from '@angular/core/testing';

import { SubordinateMenuComponent } from './subordinate-menu.component';

describe('SubordinateMenuComponent', () => {
  let component: SubordinateMenuComponent;
  let fixture: ComponentFixture<SubordinateMenuComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ SubordinateMenuComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(SubordinateMenuComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
