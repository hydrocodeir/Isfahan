import fs from 'node:fs/promises';
import { FileBlob, SpreadsheetFile } from '@oai/artifact-tool';
const root='D:/Pooya/w/GitHub/HydroCodeIR/Isfahan',out=`${root}/reports/deep_refresh_2026_10_19`;
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(process.argv.includes('--verify-final')?`${root}/Data.xlsx`:`${out}/staged/import.xlsx`));
if(process.argv.includes('--verify-final')) {
  console.log((await wb.inspect({kind:'table',range:'TRANSFER_STUDIES!A48:G50',include:'values',tableMaxRows:3,tableMaxCols:7,maxChars:1600})).ndjson);
  console.log('FINAL CANONICAL WORKBOOK IMPORTED');process.exit(0);
}
if(!process.argv.includes('--edit')) {
  console.log((await wb.inspect({kind:'sheet',include:'id,name',maxChars:1500})).ndjson);
  for(const [sheetName,range,name] of [['DASHBOARD','A1:C11','before_dashboard'],['TRANSFER_STUDIES','A28:G31','before_studies']]) {
    const b=await wb.render({sheetName,range,scale:1,format:'png'});await fs.writeFile(`${out}/${name}.png`,new Uint8Array(await b.arrayBuffer()));
  }
} else {
  const edits=JSON.parse(await fs.readFile(`${out}/workbook_changes.json`,'utf8'));
  for(const [name,op] of Object.entries(edits.append)) {
    const sheet=wb.worksheets.getItem(name);
    if(sheet.tables.items.length)sheet.tables.items[0].rows.add(null,op.rows);
    for(let i=0;i<op.rows.length;i++) {
      const dest=sheet.getRangeByIndexes(op.start_row+i-1,0,1,op.columns);
      dest.copyFrom(sheet.getRangeByIndexes(op.start_row-2,0,1,op.columns),'all');dest.values=[op.rows[i]];
      dest.format.wrapText=true;dest.format.autofitRows();
    }
  }
  const copied=new Set();
  for(const e of edits.cells) {
    const sheet=wb.worksheets.getItem(e.sheet),row=Number(e.cell.match(/\d+/)[0]);
    const oldLast=e.sheet==='DASHBOARD'?32:e.sheet==='PROJECTS'?31:null;
    if(oldLast&&row>oldLast&&!copied.has(`${e.sheet}:${row}`)) {
      sheet.getRangeByIndexes(row-1,0,1,e.sheet==='DASHBOARD'?3:2).copyFrom(sheet.getRangeByIndexes(oldLast-1,0,1,e.sheet==='DASHBOARD'?3:2),'all');
      copied.add(`${e.sheet}:${row}`);
    }
    sheet.getRange(e.cell).values=[[e.value]];
  }
  for(const item of copied) {
    const [name,row]=item.split(':');const sheet=wb.worksheets.getItem(name);
    const range=sheet.getRangeByIndexes(Number(row)-1,0,1,name==='DASHBOARD'?3:2);range.format.wrapText=true;range.format.autofitRows();
  }
  wb.recalculate();
  console.log((await wb.inspect({kind:'table',range:'DASHBOARD!A29:B35',include:'values',tableMaxRows:7,tableMaxCols:2,maxChars:1800})).ndjson);
  for(const [sheetName,range,name] of [['DASHBOARD','A29:C35','after_dashboard'],['TRANSFER_STUDIES','A32:G35','after_studies'],['TRANSFER_PROJECTS','A19:D22','after_projects']]) {
    const b=await wb.render({sheetName,range,scale:1,format:'png'});await fs.writeFile(`${out}/${name}.png`,new Uint8Array(await b.arrayBuffer()));
  }
  await (await SpreadsheetFile.exportXlsx(wb)).save(`${out}/staged/Data.xlsx`);console.log('EXPORTED');
}
