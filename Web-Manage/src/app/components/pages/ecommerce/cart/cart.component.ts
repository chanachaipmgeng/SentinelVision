import { Component } from '@angular/core';
import swal from 'sweetalert';
import { SharedModule } from '../../../../shared/shared.module';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
const DATA=[
  {
    id:'1',
    img:"./assets/images/ecommerce/png/1.png" ,
    name:'Hiroma grey Hoodie (Unisex wear)',
    size:'Large',
    color:'Grey',
    bg:'success/10',
    text:'success',
    status:'In Offer',
    price:'$459',
    total:'$918',
     quantity:'1'
  },
  {
    id:'2',
    img:"./assets/images/ecommerce/png/7.png" ,
    name:'Blue Demin Jacket for Women',
    size:'Medium',
    color:'Blue',
    bg:'secondary',
    text:'white',
    status:'25% discount',
    price:' $129',
    total:' $129',
    quantity:'1'

  },
  {
    id:'3',
    img:"./assets/images/ecommerce/png/15.png" ,
    name:'Orange smart watch(44mm dial)',
    size:'44mm dial',
    color:'Bronze',
    bg:'success/10',
    text:'success',
    status:'On Offer',
    price:' $249',
    total:' $249',
    quantity:'1'

  },
  {
    id:'4',
    img:"./assets/images/ecommerce/png/12.png" ,
    name:'Sweater for winter',
    size:'Medium',
    color:'Light Pink',
    bg:'success/10',
    text:'success',
    status:'On Offer',
    price:' $249',
    total:' $498',
    quantity:'2'

  },
  {
    id:'5',
    img:"./assets/images/ecommerce/png/3.png" ,
    name:'Snow coat from demin Corporation',
    size:'Large',
    color:'Green',
    price:'$1,299',
    total:'$1,299',
    quantity:'1'

  }
]
@Component({
  selector: 'app-cart',
  standalone: true,
  imports: [SharedModule,FormsModule,ReactiveFormsModule,CommonModule,RouterModule],
  templateUrl: './cart.component.html',
  styleUrls: ['./cart.component.scss']
})
export class CartComponent {
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
  products = DATA;
  quantity: number = 1;

  decreaseQuantity(product: any) {
    if (product.quantity > 1) {
      product.quantity--; 
      
    }
  }

  increaseQuantity(product: any) {
    product.quantity++; 

 
  }
}
