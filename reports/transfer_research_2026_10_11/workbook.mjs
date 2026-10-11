import fs from 'node:fs/promises';
import { FileBlob, SpreadsheetFile } from '@oai/artifact-tool';
const root='D:/Pooya/w/GitHub/HydroCodeIR/Isfahan';
const out=`${root}/reports/transfer_research_2026_10_11`;
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(`${root}/Data.xlsx`));
console.log((await wb.inspect({kind:'sheet',include:'id,name',maxChars:2000})).ndjson);
if(process.argv.includes('--help-panes')) {
  console.log(wb.help('worksheet.freezePanes',{include:'index,notes,examples',maxChars:3000}).ndjson);
  process.exit(0);
}
if(!process.argv.includes('--edit')) {
  for(const [sheetName,range,name] of [['DASHBOARD','A1:C11','before_dashboard'],['ALL_SOURCES','A1011:H1013','before_sources']]) {
    const b=await wb.render({sheetName,range,scale:1,format:'png'});
    await fs.writeFile(`${out}/${name}.png`,new Uint8Array(await b.arrayBuffer()));
  }
} else {
  const edits=JSON.parse(await fs.readFile(`${out}/workbook_changes.json`,'utf8'));
  for(const [name,op] of Object.entries(edits.append)) {
    const sheet=wb.worksheets.getItem(name);
    if(name==='ALL_SOURCES')sheet.tables.items[0].rows.add(null,op.rows);
    for(let i=0;i<op.rows.length;i++) {
      const dest=sheet.getRangeByIndexes(op.start_row+i-1,0,1,op.columns);
      dest.copyFrom(sheet.getRangeByIndexes(op.start_row-2,0,1,op.columns),'all');
      dest.values=[op.rows[i]]; dest.format.wrapText=true; dest.format.autofitRows();
    }
  }
  for(const e of edits.cells)wb.worksheets.getItem(e.sheet).getRange(e.cell).values=[[e.value]];
  for(const [name,op] of Object.entries(edits.new_sheets)) {
    const sheet=wb.worksheets.add(name);
    const all=sheet.getRangeByIndexes(0,0,op.rows.length,op.columns);
    all.values=op.rows; all.format.font={name:'Arial',size:11};
    all.format.wrapText=true; all.format.verticalAlignment='top'; all.format.columnWidth=28;
    sheet.getRange('A:A').format.columnWidth=16;
    sheet.getRange('B:B').format.columnWidth=48;
    const head=sheet.getRangeByIndexes(0,0,1,op.columns);
    head.format={fill:'#1B4B64',font:{name:'Arial',size:11,color:'#FFFFFF',bold:true},horizontalAlignment:'center',verticalAlignment:'center',wrapText:true,rowHeight:34};
    sheet.tables.add(`A1:${String.fromCharCode(64+op.columns)}${op.rows.length}`,true,name==='TRANSFER_PROJECTS'?'TransferProjects':'TransferStudies');
    sheet.showGridLines=false; sheet.freezePanes.freezeRows(1); sheet.freezePanes.freezeColumns(2);
    sheet.getRangeByIndexes(0,op.columns-1,op.rows.length,1).format.columnWidth=60;
    all.format.autofitRows();
  }
  wb.recalculate();
  console.log((await wb.inspect({kind:'table',range:'TRANSFER_STUDIES!A1:G3',include:'values',tableMaxRows:3,tableMaxCols:7,maxChars:2000})).ndjson);
  for(const [sheetName,range,name] of [['DASHBOARD','A28:C32','after_dashboard'],['TRANSFER_PROJECTS','A1:D4','after_projects'],['TRANSFER_STUDIES','A1:G4','after_studies']]) {
    const b=await wb.render({sheetName,range,scale:1,format:'png'});
    await fs.writeFile(`${out}/${name}.png`,new Uint8Array(await b.arrayBuffer()));
  }
  await (await SpreadsheetFile.exportXlsx(wb)).save(`${out}/staged/Data.xlsx`);
  console.log('STAGED WORKBOOK EXPORTED');
}
