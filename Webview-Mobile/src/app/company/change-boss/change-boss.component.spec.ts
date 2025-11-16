import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ChangeBossComponent } from './change-boss.component';

describe('ChangeBossComponent', () => {
  let component: ChangeBossComponent;
  let fixture: ComponentFixture<ChangeBossComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ ChangeBossComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ChangeBossComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
