import { ComponentFixture, TestBed } from '@angular/core/testing';

import { SubordinateDataComponent } from './subordinate-data.component';

describe('SubordinateDataComponent', () => {
  let component: SubordinateDataComponent;
  let fixture: ComponentFixture<SubordinateDataComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ SubordinateDataComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(SubordinateDataComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
