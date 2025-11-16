/* tslint:disable:no-unused-variable */
import { async, ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { DebugElement } from '@angular/core';

import { SubWarningTimestampMapComponent } from './sub-warning-timestamp-map.component';

describe('SubWarningTimestampMapComponent', () => {
  let component: SubWarningTimestampMapComponent;
  let fixture: ComponentFixture<SubWarningTimestampMapComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ SubWarningTimestampMapComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(SubWarningTimestampMapComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
