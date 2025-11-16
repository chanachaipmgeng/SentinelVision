/* tslint:disable:no-unused-variable */
import { async, ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { DebugElement } from '@angular/core';

import { SubordinateWarningTimestampComponent } from './subordinate-warning-timestamp.component';

describe('SubordinateWarningTimestampComponent', () => {
  let component: SubordinateWarningTimestampComponent;
  let fixture: ComponentFixture<SubordinateWarningTimestampComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ SubordinateWarningTimestampComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(SubordinateWarningTimestampComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
