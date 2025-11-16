/* tslint:disable:no-unused-variable */
import { async, ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { DebugElement } from '@angular/core';

import { PdpaComponent } from './pdpa.component';

describe('PdpaComponent', () => {
  let component: PdpaComponent;
  let fixture: ComponentFixture<PdpaComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ PdpaComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(PdpaComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
