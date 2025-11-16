export class MyCalendar{
   private _date: Date | undefined;
   
   constructor(calendar?: string) {
      this.setCalendar(calendar!);
   }
   //return [yyyy,mm,dd]
   private _splitDate(dateStr: string): number[]{
      let tmp = ["-" , "/"];
      let tmp_data : Array<any> = [];
      for(let ch of tmp){
         let idx = dateStr.indexOf(ch);
         if(idx > -1){
            tmp_data = dateStr.split(ch);
            break;
         }
      }
      if(tmp_data.length == 3){
         if(tmp_data[0].length==4){
            return [Number(tmp_data[0]) , Number(tmp_data[1]) - 1 , Number(tmp_data[2])];
         }else{
            return [Number(tmp_data[2]) , Number(tmp_data[1]) - 1 , Number(tmp_data[0])]
         }
      }else{
         throw 'format calendar invalid.'+dateStr;
      }
      
   }
   //return [hh,mm,ss]
   private _splitTime(timeStr: string): number[]{
      if(timeStr == undefined){
         return [0,0,0];
      }
      let tmp = [":" , "."];
      let tmp_data : Array<any> = [];
      for(let ch of tmp){
         let idx = timeStr.indexOf(ch);
         if(idx > -1){
            tmp_data = timeStr.split(ch);
            break;
         }
      }
      if(tmp_data.length==2 || tmp_data.length ==3){
         return [Number(tmp_data[0]) ,Number(tmp_data[1]) ,Number(tmp_data[2] || 0)  ];
      }else{
         throw 'format time invalid.'+timeStr;
      }
   }

   setCalendar(calendar: string): void{
      if(calendar == undefined || calendar == ""){
         this._date = new Date();
      }else{
         let temp = calendar.split(" ");
         let dates = this._splitDate(temp[0]);
         let times = this._splitTime(temp[1]);
         this._date = new Date(Number(dates[0]) , dates[1] , dates[2] , times[0] , times[1] , times[2]);
      }
   }

   toDate(): Date{
      return this._date!;
   }

   getTime(): string{
      return this.getHour() + "." + this.getMin();
   }

   getDDMMYYYY(): string{
      return this.getDD() + "-" + this.getMM() + "-" + this._date!.getFullYear();
   }

   getYYYYMMDD(): string{
      return this._date!.getFullYear() + "-" + this.getMM() + "-" + this.getDD();
   }

   getYYYY(): string{
      return String(this._date!.getFullYear());
   }

   getMM(): string{
      return this._date!.getMonth() < 10 ? "0"+(this._date!.getMonth()+1) : String(this._date!.getMonth()+1);
   }

   getDD(): string{
      return this._date!.getDate() < 10 ? "0"+this._date!.getDate() : String(this._date!.getDate());
   }

   getHH(): string{
      return this._2digit(this._date!.getHours());
   }

   getHour(): number{
      return this._date!.getHours();
   }

   getMinutes(): number{
      return this._date!.getMinutes();
   }

   getMin(): string{
      return this._2digit(this._date!.getMinutes());
   }

   getSS(): string{
      return this._2digit(this._date!.getSeconds());
   }

   getHHMMSS(): string{
      return this.getHH()+":"+this.getMin() +":"+this._2digit(this._date!.getSeconds());
   }

   getYYYYMMDDHHMMSS(){
      return this.getYYYYMMDD() + " " + this.getHHMMSS();
   }

   getDDMMYYYYHHMMSS(){
      return this.getDDMMYYYY() + " " + this.getHHMMSS();
   }

   private _2digit(num: number): string{
      return num < 10 ? "0"+num : num.toString();
   }

   incMonth(month?: number): void{
      this._date!.setMonth(this._date!.getMonth() + (month || 1));
   }

   decMonth(month?: number): void{
      this._date!.setMonth(this._date!.getMonth() - (month || 1))
   }

   incDate(date?: number): void{
      this._date!.setDate(this._date!.getDate() + (date || 1));
   }

   decDate(date?: number): void{
      this._date!.setDate(this._date!.getDate() - (date || 1));
   }

   incHour(hour?: number): void{
      this._date!.setHours(this._date!.getHours() + (hour || 1));
   }

   decHour(hour?: number): void{
      this._date!.setHours(this._date!.getHours() - (hour || 1));
   }

   incMin(min?: number): void{
      this._date!.setMinutes(this._date!.getMinutes() + (min || 1));
   }

   decMin(min?: number): void{
      this._date!.setMinutes(this._date!.getMinutes() - (min || 1));
   }
}