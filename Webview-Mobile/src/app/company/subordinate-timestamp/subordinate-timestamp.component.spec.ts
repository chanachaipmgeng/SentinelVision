import { ComponentFixture, TestBed } from '@angular/core/testing';

import { SubordinateTimestampComponent } from './subordinate-timestamp.component';

describe('SubTimestampCriteriaComponent', () => {
  let component: SubordinateTimestampComponent;
  let fixture: ComponentFixture<SubordinateTimestampComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ SubordinateTimestampComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(SubordinateTimestampComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
