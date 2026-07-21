import { Pipe, PipeTransform } from "@angular/core";

@Pipe({
  name: "thaidate",
})
export class ThaiDatePipe implements PipeTransform {
  transform(date: string, format: string): string {
    // console.log(date);
    let ThaiDay = [
      "อาทิตย์",
      "จันทร์",
      "อังคาร",
      "พุธ",
      "พฤหัสบดี",
      "ศุกร์",
      "เสาร์",
    ];
    let shortThaiMonth = [
      "ม.ค.",
      "ก.พ.",
      "มี.ค.",
      "เม.ย.",
      "พ.ค.",
      "มิ.ย.",
      "ก.ค.",
      "ส.ค.",
      "ก.ย.",
      "ต.ค.",
      "พ.ย.",
      "ธ.ค.",
    ];
    let longThaiMonth = [
      "มกราคม",
      "กุมภาพันธ์",
      "มีนาคม",
      "เมษายน",
      "พฤษภาคม",
      "มิถุนายน",
      "กรกฎาคม",
      "สิงหาคม",
      "กันยายน",
      "ตุลาคม",
      "พฤศจิกายน",
      "ธันวาคม",
    ];
    let inputDate = new Date(date);
    let dataDate = [
      inputDate.getDay(),
      inputDate.getDate(),
      inputDate.getMonth(),
      inputDate.getFullYear(),
    ];
    let outputThaiDay = [
      ThaiDay[dataDate[0]],
    ];
    let outputDateFull = [
      "วัน " + ThaiDay[dataDate[0]],
      "ที่ " + dataDate[1],
      "เดือน " + longThaiMonth[dataDate[2]],
      "พ.ศ. " + (dataDate[3] + 543),
    ];
    let outputDateFullSpace = [
      "วัน" + ThaiDay[dataDate[0]],
      "ที่ " + dataDate[1],
      " " + longThaiMonth[dataDate[2]],
      " พ.ศ. " + (dataDate[3] + 543),
    ];
    let outputDateFullNoMonth = [
      "วัน" + ThaiDay[dataDate[0]],
      "ที่ " + dataDate[1],
      " " + longThaiMonth[dataDate[2]],
      "พ.ศ. " + (dataDate[3] + 543),
    ];
    let outputDateDayMonthYearฺByYearMonthDay = [
      longThaiMonth[dataDate[2]],
      "พ.ศ. " + (dataDate[3] + 543),
    ];
    let outputDateFullNoYear = [
      "วัน" + ThaiDay[dataDate[0]],
      "ที่ " + dataDate[1],
      " " + longThaiMonth[dataDate[2]],
      " " + (dataDate[3] + 543),
    ];
    let outputDateShort = [
      dataDate[1],
      shortThaiMonth[dataDate[2]],
      dataDate[3] + 543,
    ];
    let outputDateMedium = [
      dataDate[1],
      longThaiMonth[dataDate[2]],
      dataDate[3] + 543,
    ];
    let returnDate: string;
    returnDate = outputDateMedium.join(" ");
    if (format == "day") {
      returnDate = outputThaiDay.join(" ");
    }
    if (format == "full") {
      returnDate = outputDateFull.join(" ");
    }
    if (format == "medium") {
      returnDate = outputDateMedium.join(" ");
    }
    if (format == "short") {
      returnDate = outputDateShort.join(" ");
    }
    if (format == "fullNotMonth") {
      returnDate = outputDateFullNoMonth.join("");
    }
    if (format == "fullNotYear") {
      returnDate = outputDateFullNoYear.join("");
    }
    if (format == "fullSpace"){
      returnDate  = outputDateFullSpace.join("");
    }
    if (format == "dayMonthYear") {
      returnDate = outputDateDayMonthYearฺByYearMonthDay.join(" ");
    }
    return returnDate;
  }
}
