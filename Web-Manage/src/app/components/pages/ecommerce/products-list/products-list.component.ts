import { Component } from '@angular/core';
import { SharedModule } from '../../../../shared/shared.module';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
const DATA=[
  {
    id:'1',
    img:"./assets/images/ecommerce/png/1.png",
    name:'DapZem & Co Blue Hoodie',
    category:"Clothing",
    price:'$1,299 ',
    stock:'283',
    gender:'Male',
    seller:"Apilla.co.in ",
    published:"24,Nov 2022 - 04:42PM"
  },
  {
    id:'2',
    img:"./assets/images/ecommerce/png/2.png",
    name:'Leather jacket for men',
    category:"Clothing",
    price:'$799 ',
    stock:'98',
    gender:'Male',
    seller:"Donzo Company ",
    published:"18,Nov 2022 - 06:53AM"
  },
  {
    id:'3',
    img:"./assets/images/ecommerce/png/15.png",
    name:'Orange Smart Watch',
    category:"Watches",
    price:'$349 ',
    stock:'1,293',
    gender:'Male,Female',
    seller:"SlowTrack Company ",
    published:"21,Oct 2022 - 11:36AM"
  },
    {
    id:'4',
    img:"./assets/images/ecommerce/png/3.png",
    name:'Winter Coat For Women',
    category:"Clothing",
    price:'$189 ',
    stock:'322',
    gender:'Female',
    seller:"WoodHill.co.in ",
    published:"16,Oct 2022 - 12:45AM"
  },
  {
    id:'5',
    img:"./assets/images/ecommerce/png/4.png",
    name:'Vintage White Full Sleeve Tee-Shirt',
    category:"Clothing",
    price:'$2,499',
    stock:'194',
    gender:'Male,Female',
    seller:"Watches.co.in",
    published:"12,Aug 2022 - 11:21AM"
  },
  {
    id:'6',
    img:"./assets/images/ecommerce/png/13.png",
    name:' Orange Watch series (44mm)',
    category:"Watches",
    price:'$899',
    stock:'267',
    gender:'Male,Female',
    seller:"Watches.co.in",
    published:"05,Sep 2022 - 10:14AM"
  },
  {
    id:'7',
    img:"./assets/images/ecommerce/png/12.png",
    name:'Sweater For Women',
    category:"Clothing",
    price:'$499',
    stock:'143',
    gender:'Female',
    seller:"Louie Philippe",
    published:"18,Nov 2022 - 14:35PM"
  },
  {
    id:'8',
    img:"./assets/images/ecommerce/png/16.png",
    name:'Ikonic Smart Watch(40mm)',
    category:"Clothing",
    price:'$999',
    stock:'365',
    gender:'Female',
    seller:"Kohino.zaps.com",
    published:"27,Nov 2022 - 05:12AM"
  },
  {
    id:'9',
    img:"./assets/images/ecommerce/png/23.png",
    name:'Appole Watch Series 5',
    category:"Watches",
    price:'$1,499',
    stock:'257',
    gender:'Male,Female',
    seller:"Appole Corporation",
    published:"29,Nov 2022 - 16:32AM"
  },

]
@Component({
  selector: 'app-products-list',
  standalone: true,
  imports: [SharedModule,CommonModule,RouterModule],
  templateUrl: './products-list.component.html',
  styleUrls: ['./products-list.component.scss']
})
export class ProductsListComponent {
  click=(id:string)=>{
    const data = this.products.filter((x: { id: string }) => {
      return x.id != id;
    });
    this.products = data;

  }
products=DATA;
}
