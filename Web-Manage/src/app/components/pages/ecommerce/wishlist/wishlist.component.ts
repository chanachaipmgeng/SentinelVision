import { Component } from '@angular/core';
import swal from 'sweetalert';
import { SharedModule } from '../../../../shared/shared.module';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';

const DATA=[
  {
id:'1',
img:"./assets/images/ecommerce/png/1.png",
name:'Dapzem & Co',
rating:'4.2',
type:'Branded hoodie ethnic style',
price:'$229',
price2:'$1,799',
percent:'72% off',
offerPrice:'229'
  },
  {
   id:'2',
  img:"./assets/images/ecommerce/png/2.png",
  name:'Denim Winjo',
  rating:'4.2',
  type:'Vintage pure leather Jacket',
  price:'$599',
  price2:'$2,499',
  percent:'75% off',
  offerPrice:'599'
   },
{
  id:'3',
  img:"./assets/images/ecommerce/png/3.png",
  name:'Unisex jacket for men & women',
  rating:'4.2',
  type:'Vintage pure leather Jacket',
  price:'$1,199',
  price2:'$3,299',
  percent:'62% off',
  offerPrice:'1,199'
 },
 {
id:'4',
img:"./assets/images/ecommerce/png/4.png",
name:'Bluberry Co.In',
rating:'4.2',
type:'Full sleeve white hoodie',
price:'$399',
price2:'$1,299',
percent:'60% off',
offerPrice:'399'
  },
  {
 id:'5',
 img:"./assets/images/ecommerce/png/5.png",
 name:'Aus Polo Assn',
 rating:'4.2',
 type:'Snow jacket with low pockets',
 price:'$1,899',
 price2:'$3,799',
 percent:'50% off',
 offerPrice:'1,899'
},
{
  id:'6',
  img:"./assets/images/ecommerce/png/6.png",
  name:'BMW',
  rating:'4.2',
  type:'Ethnic wear jackets form BMW',
  price:'$1,499',
  price2:'$2,499',
  percent:'38% off',
  offerPrice:'1,499'
 },
 {
id:'7',
img:"./assets/images/ecommerce/png/7.png",
name:'Denim Corporation',
rating:'4.2',
type:'Flap pockets denim jackets for men',
price:'$299',
price2:'$399',
percent:'35% off',
offerPrice:'299'
  },
  {
 id:'8',
 img:"./assets/images/ecommerce/png/8.png",
 name:'Pufa',
 rating:'4.2',
 type:'Ergonic designed full sleeve coat',
 price:'$2,399',
 price2:'$5,699',
 percent:'72% off',
 offerPrice:'2,399'
},
{
  id:'9',
  img:"./assets/images/ecommerce/png/9.png",
  name:'Louie Phillippe',
  rating:'4.2',
  type:'Ergonic green colored full sleeve jacket',
  price:'$1,899',
  price2:'$3,299',
  percent:'60% off',
  offerPrice:'1,899'
 },
 {
id:'10',
img:"./assets/images/ecommerce/png/10.png",
name:'Denim Corp',
rating:'4.1',
type:'beautiful brown colored snow jacket',
price:'$2,499',
price2:'$4,999',
percent:'50% off',
offerPrice:'2,499'
  },
  {
    id:'11',
    img:"./assets/images/ecommerce/png/11.png",
    name:'Garage & Co',
    rating:'4.1',
    type:'Full sleeve sweat shirt',
    price:'$249',
    price2:'$1,299',
    percent:'70% off',
    offerPrice:'249'
      },
      {
        id:'12',
        img:"./assets/images/ecommerce/png/12.png",
        name:'Blueberry & Co',
        rating:'4.1',
        type:'Light colored sweater form blueberry',
        price:'$499',
        price2:'$799',
        percent:'32% off',
        offerPrice:'499'
          },
]
@Component({
  selector: 'app-wishlist',
  standalone: true,
  imports: [SharedModule,CommonModule,RouterModule],
  templateUrl: './wishlist.component.html',
  styleUrls: ['./wishlist.component.scss']
})
export class WishlistComponent {
  products=DATA;
  ConformAlert(id:string) {
    swal({
        title: "Are you sure?",
        text: "You won't be able to revert this!",
        icon: "warning",
        dangerMode: true,
        buttons: ["Cancel", "Yes,Delete it!"],
      })
      .then((willDelete: any) => {
        if (willDelete) {
         const data = this.products.filter((x: { id: string }) => x.id !== id);
         this.products = data;
          swal("Deleted!", "Your imaginary file has been deleted!", "success");
        }
        else {
         // User clicked "Cancel" or closed the alert
         swal("Cancelled", "Your item is safe :)", "info");
       }
      });
     
     }
}
