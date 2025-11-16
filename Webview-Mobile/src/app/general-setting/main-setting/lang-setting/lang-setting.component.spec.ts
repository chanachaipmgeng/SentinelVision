/* tslint:disable:no-unused-variable */
import { async, ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { DebugElement } from '@angular/core';

import { LangSettingComponent } from './lang-setting.component';

describe('LangSettingComponent', () => {
  let component: LangSettingComponent;
  let fixture: ComponentFixture<LangSettingComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ LangSettingComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(LangSettingComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
