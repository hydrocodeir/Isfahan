import fs from 'node:fs/promises';
import { FileBlob, SpreadsheetFile } from '@oai/artifact-tool';
const root = 'D:/Pooya/w/GitHub/HydroCodeIR/Isfahan';
const out = `${root}/reports/merge_deep_round2_2026_10_10`;
const wb = await SpreadsheetFile.importXlsx(await FileBlob.load(`${root}/Data.xlsx`));
console.log((await wb.inspect({kind:'workbook',maxChars:5000})).ndjson);
if(process.argv.includes('--verify-final')) {
 for(const [sheetName,range,name] of [['DASHBOARD','A1:C11','final_dashboard'],['ALL_SOURCES','A1010:H1013','final_documents']]) {
  const b=await wb.render({sheetName,range,scale:1,format:'png'});
  await fs.writeFile(`${out}/${name}.png`,new Uint8Array(await b.arrayBuffer()));
 }
 console.log('FINAL PREVIEW COMPLETE');process.exit(0);
}
if(process.argv.includes('--help-links')) {
 console.log(wb.help('range.hyperlink',{include:'index,notes,examples',maxChars:3500}).ndjson);
 process.exit(0);
}
if(process.argv.includes('--edit')) {
 const edits=JSON.parse(await fs.readFile(`${out}/workbook_changes.json`,'utf8'));
 for(const [name,op] of Object.entries(edits.append)) {
  const sheet=wb.worksheets.getItem(name);
  if(name==='ALL_SOURCES') sheet.tables.items[0].rows.add(null,op.rows);
  for(let i=0;i<op.rows.length;i++) {
   const dest=sheet.getRangeByIndexes(op.start_row+i-1,0,1,op.columns);
   dest.copyFrom(sheet.getRangeByIndexes(op.start_row-2,0,1,op.columns),'all');
   dest.values=[op.rows[i]];
   dest.format.wrapText=true;
   dest.format.autofitRows();
  }
 }
 for(const e of edits.cells)wb.worksheets.getItem(e.sheet).getRange(e.cell).values=[[e.value]];
 wb.recalculate();
 console.log((await wb.inspect({kind:'table',range:'DASHBOARD!A2:B11',include:'values',tableMaxRows:10,tableMaxCols:2})).ndjson);
 for(const [sheetName,range,name] of [['DASHBOARD','A1:C11','after_dashboard'],['ALL_SOURCES','A987:H990','after_sources']]) {
  const b=await wb.render({sheetName,range,scale:1,format:'png'});
  await fs.writeFile(`${out}/${name}.png`,new Uint8Array(await b.arrayBuffer()));
 }
 await (await SpreadsheetFile.exportXlsx(wb)).save(`${out}/staged/Data.xlsx`);
 console.log('STAGED WORKBOOK EXPORTED');
 process.exit(0);
}
for (const [sheetName,range,name] of [['DASHBOARD','A1:C10','before_dashboard'],['ALL_SOURCES','A982:H986','before_sources']]) {
  const b = await wb.render({sheetName,range,scale:1,format:'png'});
  await fs.writeFile(`${out}/${name}.png`,new Uint8Array(await b.arrayBuffer()));
}
