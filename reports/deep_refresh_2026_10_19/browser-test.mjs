import fs from 'node:fs/promises';
import path from 'node:path';
import http from 'node:http';
import assert from 'node:assert/strict';
import {chromium} from 'playwright';
const root='D:/Pooya/w/GitHub/HydroCodeIR/Isfahan',out=`${root}/reports/deep_refresh_2026_10_19`,live=process.argv.includes('--live');
const data=JSON.parse(await fs.readFile(`${live?root:out+'/staged'}/data.json`,'utf8'));
const manifest=JSON.parse(await fs.readFile(`${out}/manifest.json`,'utf8'));
const server=http.createServer(async(req,res)=>{
 try {
  const pathname=decodeURIComponent(new URL(req.url,'http://localhost').pathname);let file=path.resolve(root,'.'+(pathname==='/'?'/index.html':pathname));
  if(!file.startsWith(path.resolve(root)+path.sep)){res.writeHead(403);res.end();return;}
  if(!live&&['data.json','app.js'].includes(path.basename(file)))file=`${out}/staged/${path.basename(file)}`;
  const mime={'.html':'text/html','.js':'text/javascript','.css':'text/css','.json':'application/json'};
  res.setHeader('Content-Type',(mime[path.extname(file)]||'text/plain')+'; charset=utf-8');res.end(await fs.readFile(file));
 }catch{res.writeHead(404);res.end();}
});
await new Promise(r=>server.listen(0,'127.0.0.1',r));let browser;
try {
 browser=await chromium.launch({headless:true,channel:'chrome'});const page=await browser.newPage({viewport:{width:1440,height:1000},acceptDownloads:true});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.route('https://**/*',route=>route.abort());
 const url=`http://127.0.0.1:${server.address().port}/`;await page.goto(url);await page.waitForFunction(()=>document.querySelector('#navStudiesCount').textContent==='۴۹');
 assert.equal(await page.evaluate(()=>state.sources.length),1067);
 await page.locator('[data-view="studies"]').click();assert.equal(await page.locator('#studyTableBody tr').count(),49);
 assert((await page.locator('#studyCountingNote').textContent()).includes('۴۹'));
 await page.locator('#studySearch').fill('Nippon');assert.equal(await page.locator('#studyTableBody tr').count(),1);
 await page.locator('[data-study]').first().click();assert((await page.locator('#modalContent').textContent()).includes('حمایت مالی'));
 await page.locator('#modalContent [data-registry-source]').first().click();assert((await page.locator('#modalContent').textContent()).includes('GRIPS'));
 await page.locator('.modal-close').click();await page.locator('#studyClearBtn').click();
 await page.locator('#studyProject').selectOption('WT-T24');assert.equal(await page.locator('#studyTableBody tr').count(),1);
 await page.locator('#studyClearBtn').click();await page.locator('#studyProvince').selectOption('کهگیلویه و بویراحمد');assert(await page.locator('#studyTableBody tr').count()>=4);
 await page.locator('#studyClearBtn').click();await page.locator('#studyCooperation').selectOption('international');assert.equal(await page.locator('#studyTableBody tr').count(),data.transferResearch.studies.filter(s=>s.cooperation_type==='international').length);
 await page.locator('#studyClearBtn').click();await page.locator('#studySearch').fill('no-such-study-20261019');assert((await page.locator('#studyTableBody').textContent()).includes('پیدا نشد'));
 await page.locator('#studyClearBtn').click();
 const downloadEvent=page.waitForEvent('download');await page.locator('#studyExportBtn').click();await(await downloadEvent).saveAs(`${out}/studies_export.csv`);
 const csv=await fs.readFile(`${out}/studies_export.csv`,'utf8');assert(csv.includes('WT-R49')&&csv.includes('S097')&&csv.includes('https://'));
 await page.locator('[data-view="projects"]').click();assert.equal(await page.locator('#transferProjectCatalog details').count(),25);
 await page.locator('#projectSearch').fill('دهدشت');assert.equal(await page.locator('#transferProjectCatalog details').count(),1);
 await page.locator('#transferProjectCatalog summary').click();await page.locator('[data-project-studies="WT-T24"]').click();assert.equal(await page.locator('#studyProject').inputValue(),'WT-T24');
 await page.locator('[data-view="sources"]').click();await page.locator('#filterProject').selectOption('تأمین و انتقال آب دهدشت غربی');assert(await page.evaluate(()=>state.filtered.length)>0);
 await page.locator('#clearFiltersBtn').click();
 for(const id of manifest.added_source_ids) {
  await page.evaluate(id=>openSource(id),id);assert((await page.locator('#modalContent').textContent()).includes(id));
  assert(await page.locator('#modalContent a').first().getAttribute('href')!=='#');await page.locator('.modal-close').click();
 }
 await page.evaluate(()=>openSource('S097'));assert.equal(await page.locator('#modalContent a[href^="https://doi.org/"]').getAttribute('href'),'https://doi.org/10.22111/gdij.2021.6027');await page.locator('.modal-close').click();
 await page.locator('[data-view="studies"]').click();await page.locator('#studyClearBtn').click();await page.locator('#studySearch').fill('خرسان');
 await page.screenshot({path:`${out}/dashboard_refresh.png`});await page.locator('#studyClearBtn').click();
 await page.locator('#themeToggleBtn').click();await page.waitForFunction(()=>getComputedStyle(document.querySelector('#view-studies .filter-panel')).backgroundColor==='rgb(24, 28, 32)');
 await page.screenshot({path:`${out}/dashboard_dark.png`});await page.setViewportSize({width:390,height:844});await page.waitForFunction(()=>getComputedStyle(document.querySelector('#sidebar')).visibility==='hidden');
 await page.screenshot({path:`${out}/dashboard_mobile.png`});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth));
 const offline=await browser.newPage();offline.on('pageerror',e=>errors.push(e.message));await offline.route('https://**/*',route=>route.abort());await offline.route('**/data.json',route=>route.abort());
 await offline.goto(url);await offline.waitForFunction(()=>document.querySelector('#navStudiesCount').textContent==='۴۹');assert.equal(await offline.evaluate(()=>state.sources.length),1067);
 await offline.locator('[data-view="studies"]').click();assert.equal(await offline.locator('#studyTableBody tr').count(),49);assert.deepEqual(errors,[]);
 await fs.writeFile(`${out}/browser_validation.json`,JSON.stringify({status:'PASS',mode:live?'canonical':'staged',sources:1067,studies:49,projects:25,filters:true,new_source_modals:25,export:true,mobile:true,dark_theme:true,offline_fallback:true,page_errors:errors},null,2));
 console.log('PASS: 1067 sources, 49 studies, 25 profiles; all new modals, filters, CSV and offline mode.');
}finally{if(browser)await browser.close();await new Promise(r=>server.close(r));}
