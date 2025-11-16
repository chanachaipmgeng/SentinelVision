/* tslint:disable:no-unused-variable */
import { async, ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { DebugElement } from '@angular/core';

import { SubordinateWarningComponent } from './subordinate-warning.component';

describe('SubordinateWarningComponent', () => {
  let component: SubordinateWarningComponent;
  let fixture: ComponentFixture<SubordinateWarningComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ SubordinateWarningComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(SubordinateWarningComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
