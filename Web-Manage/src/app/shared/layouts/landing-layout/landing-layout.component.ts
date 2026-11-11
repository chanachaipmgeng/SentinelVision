import { Component } from '@angular/core';
import { RouterModule } from '@angular/router';
import { LandingSwitcherComponent } from '../../components/landing-switcher/landing-switcher.component';

@Component({
    selector: 'app-landing-layout',
    imports: [RouterModule, LandingSwitcherComponent],
    templateUrl: './landing-layout.component.html',
    styleUrl: './landing-layout.component.scss',
})
export class LandingLayoutComponent {


}
