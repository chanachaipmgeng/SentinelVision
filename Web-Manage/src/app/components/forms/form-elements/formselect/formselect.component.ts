import { Component } from '@angular/core';
import { FormControl, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { NgSelectModule } from '@ng-select/ng-select';
import { SharedModule } from '../../../../shared/shared.module';

@Component({
  selector: 'app-formselect',
  standalone: true,
  imports: [SharedModule,NgSelectModule,FormsModule,ReactiveFormsModule],
  templateUrl: './formselect.component.html',
  styleUrl: './formselect.component.scss'
})
export class FormselectComponent {
  selectedCompany: any;
  selectedCompanies: any;
  selectedOptions:any
  options=['one','two','three','four']
  uniqueOptions=['child1','child2']
  companies: any[] = [];
  companiesNames = ['Alabama', 'Alaska', 'Arizona','Arkansas','Colorado','Connecticut',
   'Delaware','District of Columbia','Florida','Georgia', 'Hawaii', 'Idaho', 'Illinois',
   'Indiana','Iowa','Kansas','Kentucky','Louisiana','Maine','Maryland', 'Massachusetts',
   'Michigan','Minnesota','Mississippi','Missouri','Montana','Nebraska','Nevada','New Hampshire','New Jersey', 'New Mexico',
  ' New York', ' North Carolina', 'North Dakota','Ohio','Oklahoma','Oregon','Pennsylvania',
'Rhode Island', 'South Carolina','South Dakota','Tennessee','Texas', 'Utah','Vermont','Virginia',
  'Washington','West Virginia','Wisconsin','Wyoming' ];

  selectedChoices: any;
  choices: any[] = [];
  ChoicesList1 = [
    'Choice 1',
    'Choice 2',
    'Choice 3',
    'Choice 4',
    'Choice 5',
  ];
  selectedChoices2: any;
  choices2: any[] = [];
  ChoicesList2 = ['Choice 1', 'Choice 2', 'Choice 3','Choice 4'];

  selectedAccount = 'Adam';
  accounts = [
    {
      name: 'Adam',
      email: 'adam@email.com',
      age: 12,
      country: 'United States',
      child: { state: 'Active' },
    },
    {
      name: 'Homer',
      email: 'homer@email.com',
      age: 47,
      country: '',
      child: { state: 'Active' },
    },
    {
      name: 'Samantha',
      email: 'samantha@email.com',
      age: 30,
      country: 'United States',
      child: { state: 'Active' },
    },
    {
      name: 'Amalie',
      email: 'amalie@email.com',
      age: 12,
      country: 'Argentina',
      child: { state: 'Active' },
    },
    {
      name: 'Estefanía',
      email: 'estefania@email.com',
      age: 21,
      country: 'Argentina',
      child: { state: 'Active' },
    },
    {
      name: 'Adrian',
      email: 'adrian@email.com',
      age: 21,
      country: 'Ecuador',
      child: { state: 'Active' },
    },
    {
      name: 'Wladimir',
      email: 'wladimir@email.com',
      age: 30,
      country: 'Ecuador',
      child: { state: 'Inactive' },
    },
    {
      name: 'Natasha',
      email: 'natasha@email.com',
      age: 54,
      country: 'Ecuador',
      child: { state: 'Inactive' },
    },
    {
      name: 'Nicole',
      email: 'nicole@email.com',
      age: 43,
      country: 'Colombia',
      child: { state: 'Inactive' },
    },
    {
      name: 'Michael',
      email: 'michael@email.com',
      age: 15,
      country: 'Colombia',
      child: { state: 'Inactive' },
    },
    {
      name: 'Nicolás',
      email: 'nicole@email.com',
      age: 43,
      country: 'Colombia',
      child: { state: 'Inactive' },
    },
  ];

  groupByFn = (item: any) => item.child.state;

  groupValueFn = (_: string, children: any[]) => ({
    name: children[0].child.state,
    total: children.length,
  });

  ngOnInit() {
    this.companiesNames.forEach((c, i) => {
      this.companies.push({ id: i, name: c });
    });
    this.ChoicesList1.forEach((c: any, i: any) => {
      this.choices.push({ id: i, name: c });
    });
    this.ChoicesList2.forEach((c: any, i: any) => {
      this.choices2.push({ id: i, name: c });
    });
  }

  addTagFn(name: any) {
    return { name: name, tag: true };
  }
  multiSelectSelected = ['Manchester'];
  multiSelect = [
    {
      name: 'London',
      child: { state: 'UK' },
    },
    {
      name: 'Liverpool',
      child: { state: 'UK' },
    },
    {
      name: 'Paris',
      child: { state: 'FR' },
    },
    {
      name: 'Lyon',
      child: { state: 'FR' },
    },
    {
      name: 'Marseille',
      child: { state: 'FR' },
    },
    {
      name: 'Hamburg',
      child: { state: 'DE' },
    },
    {
      name: 'Munich',
      child: { state: 'DE' },
    },
    {
      name: 'Berlin',
      child: { state: 'DE' },
    },
    {
      name: 'New York',
      child: { state: 'US' },
    },
    {
      name: 'Washington',
      child: { state: 'US' },
    },
    {
      name: 'Michigan',
      child: { state: 'US' },
    },
    {
      name: 'Madrid',
      child: { state: 'SP' },
    },
    {
      name: 'Barcelona',
      child: { state: 'SP' },
    },
    {
      name: 'Malaga',
      child: { state: 'SP' },
    },
  ];
  email: string = '';
  emailFormControl = new FormControl('', [
    Validators.required,
    Validators.email,
  ]);
}
