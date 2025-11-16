/* tslint:disable:no-unused-variable */
import { async, ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { DebugElement } from '@angular/core';

import { DocReferComponent } from './doc-refer.component';

describe('DocReferComponent', () => {
  let component: DocReferComponent;
  let fixture: ComponentFixture<DocReferComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ DocReferComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(DocReferComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
