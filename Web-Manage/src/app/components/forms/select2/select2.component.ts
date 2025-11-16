import { Component } from '@angular/core';
import { SharedModule } from '../../../shared/shared.module';
import { NgSelectModule } from '@ng-select/ng-select';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';

@Component({
  selector: 'app-select2',
  standalone: true,
  imports: [SharedModule,NgSelectModule,FormsModule,ReactiveFormsModule],
  templateUrl: './select2.component.html',
  styleUrls: ['./select2.component.scss']
})
export class Select2Component {

  genders = [
    {id: 1,name: 'Texas'},
    {id: 2,name: 'Georgia'},
    {id: 3,name: 'California'},
    {id: 4,name: 'Washington D.C'},
    {id: 5,name: 'Virginia'},

  ];
  selectedGender = this.genders[1].name;
  templates = [
    {
      id: 1,
      name: 'Andrew',
      avatar: './assets/images/faces/select2/p-5.jpg',
      value:'p-1'
    },
    {
      id: 2,
      name: 'Maya',
      avatar: './assets/images/faces/select2/p-4.jpg',
      value:'p-2'
    },
    {
      id: 3,
      name: 'Brodus Axel',
      avatar: './assets/images/faces/select2/p-2.jpg',
      value:'p-3'
    },
    {
      id: 4,
      name: 'Goldens',
      avatar: './assets/images/faces/select2/p-1.jpg',
      value:'p-4'
    },
    {
      id: 5,
      name: 'Angelina',
      avatar: './assets/images/faces/select2/p-2.jpg',
      value:'p-5'
    },

  ];
  selectedTemplate = this.templates[1].name;
  simpleItems2: any = [];
  selectedCars2 = ['Andrew'];
  cars2 = [
    { id: 1, name: 'Maya' },
    { id: 2, name: 'Brodus Axel'},
    { id: 3, name: 'Goldhens' },
    { id: 4, name: 'Angelina' },
  ];
  selectedSimpleItem3= 'Selection-4';
  simpleItems3: any = [
    {id:1,name:'Selection-1'},
    {id:2,name:'Selection-2'},
    {id:3,name:'Selection-3'},
    {id:4,name:'Selection-4'}



  ];
  selectedCars3 = ['Volvo'];
  cars3= [
    { id: 1, name: 'Volvo' },
    { id: 2, name: 'Saab'},
    { id: 3, name: 'Opel' },
    { id: 4, name: 'Audi' },
  ];
  isCarsDisabled = false;
  enable() {
    this.isCarsDisabled = false;
  }
  disable(){
    this.isCarsDisabled = !this.isCarsDisabled;
  }
  selectedCars = ['Multiple-1'];
  cars = [
    { id: 1, name: 'Multiple-1' },
    { id: 2, name: 'Multiple-2'},
    { id: 3, name: 'Multiple-3' },
    { id: 4, name: 'Multiple-4' },
  ];
  selectedSimpleItem2 = 'Appple';
  cars1 = [
    { id: 1, name: 'Mango' },
    { id: 2, name: 'Orange' },
    { id: 3, name: 'Guava' },
    { id: 4, name: 'Pineapple' },
  ];
}
