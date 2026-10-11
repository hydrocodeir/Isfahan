import fs from 'node:fs/promises';
import http from 'node:http';
import path from 'node:path';
import assert from 'node:assert/strict';
import { chromium } from 'playwright';
const root='D:/Pooya/w/GitHub/HydroCodeIR/Isfahan';
const out=`${root}/reports/transfer_research_2026_10_11`;
const live=process.argv.includes('--live');
const data=JSON.parse(await fs.readFile(`${live?root:out+'/staged'}/data.json`,'utf8'));
const server=http.createServer(async(req,res)=>{
  try {
    const pathname=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
    let file=path.resolve(root,'.'+(pathname==='/'?'/index.html':pathname));
    if(!file.startsWith(path.resolve(root)+path.sep)){res.writeHead(403);res.end();return;}
    if(!live&&['data.json','app.js'].includes(path.basename(file)))file=`${out}/staged/${path.basename(file)}`;
    const mime={'.html':'text/html','.js':'text/javascript','.css':'text/css','.json':'application/json'};
    res.setHeader('Content-Type',(mime[path.extname(file)]||'text/plain')+'; charset=utf-8');res.end(await fs.readFile(file));
  }catch{res.writeHead(404);res.end();}
});
await new Promise(r=>server.listen(0,'127.0.0.1',r));
let browser;
try {
  browser=await chromium.launch({headless:true,channel:'chrome'});
  const page=await browser.newPage({viewport:{width:1440,height:1000},acceptDownloads:true});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.route('https://**/*',route=>route.abort());
  const url=`http://127.0.0.1:${server.address().port}/`;
  await page.goto(url);await page.waitForFunction(()=>document.querySelector('#navStudiesCount').textContent==='۳۰');
  assert.equal(await page.evaluate(()=>state.sources.length),1042);
  await page.locator('[data-view="studies"]').click();
  assert.equal(await page.locator('#studyTableBody tr').count(),30);
  assert.equal(await page.locator('#studyProject option').count(),19);
  await page.screenshot({path:`${out}/dashboard_studies.png`});
  await page.locator('#studyCooperation').selectOption('international');
  assert.equal(await page.locator('#studyTableBody tr').count(),data.transferResearch.studies.filter(s=>s.cooperation_type==='international').length);
  await page.locator('#studyClearBtn').click();await page.locator('#studyProvince').selectOption('خوزستان');
  assert(await page.locator('#studyTableBody tr').count()>0);
  await page.locator('#studyClearBtn').click();await page.locator('#studySearch').fill('کریت');
  assert(await page.locator('#studyTableBody tr').count()>=3);
  await page.locator('#studyClearBtn').click();await page.locator('#studySearch').fill('no-such-study-20261011');
  assert((await page.locator('#studyTableBody').textContent()).includes('پیدا نشد'));
  await page.locator('#studyClearBtn').click();await page.locator('[data-study="WT-R30"]').click();
  await page.locator('#sourceModal.open').waitFor();assert((await page.locator('#modalContent').textContent()).includes('۲۹۸'));
  await page.locator('#modalContent [data-registry-source]').first().click();
  assert((await page.locator('#modalContent').textContent()).includes('S397'));
  await page.locator('.modal-close').click();
  const downloadEvent=page.waitForEvent('download');await page.locator('#studyExportBtn').click();
  const download=await downloadEvent;await download.saveAs(`${out}/studies_export.csv`);
  const csv=await fs.readFile(`${out}/studies_export.csv`,'utf8');assert(csv.includes('WT-R30')&&csv.includes('S397')&&csv.includes('https://'));
  await page.locator('[data-view="projects"]').click();assert.equal(await page.locator('#transferProjectCatalog details').count(),17);
  const project=page.locator('#transferProjectCatalog details').filter({has:page.locator('[data-project-studies="WT-T10"]')});
  await project.locator('summary').click();await project.locator('[data-project-studies]').click();
  assert.equal(await page.locator('#studyProject').inputValue(),'WT-T10');
  assert.equal(await page.locator('#studyTableBody tr').count(),data.transferResearch.studies.filter(s=>s.project_ids.includes('WT-T10')).length);
  await page.locator('[data-view="projects"]').click();await page.locator('#projectSearch').fill('غدیر');assert.equal(await page.locator('#transferProjectCatalog details').count(),1);
  await page.locator('[data-view="sources"]').click();await page.locator('#filterProvince').selectOption('کهگیلویه و بویراحمد');
  assert(await page.evaluate(()=>state.filtered.length)>0);
  await page.locator('#clearFiltersBtn').click();await page.locator('#filterProject').selectOption('غدیر خوزستان');assert(await page.evaluate(()=>state.filtered.length)>0);
  await page.locator('#clearFiltersBtn').click();
  await page.locator('[data-view="studies"]').click();await page.locator('#studyClearBtn').click();
  await page.locator('#themeToggleBtn').click();
  await page.waitForFunction(()=>getComputedStyle(document.querySelector('#view-studies .filter-panel')).backgroundColor==='rgb(24, 28, 32)');
  await page.screenshot({path:`${out}/dashboard_studies_dark.png`});
  await page.setViewportSize({width:390,height:844});
  await page.waitForFunction(()=>getComputedStyle(document.querySelector('#sidebar')).visibility==='hidden');
  await page.screenshot({path:`${out}/dashboard_studies_mobile.png`});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth));
  // Verify file://-equivalent fetch failure uses the embedded, identical dataset.
  const offline=await browser.newPage();offline.on('pageerror',e=>errors.push(e.message));
  await offline.route('https://**/*',route=>route.abort());await offline.route('**/data.json',route=>route.abort());
  await offline.goto(url);await offline.waitForFunction(()=>document.querySelector('#navStudiesCount').textContent==='۳۰');
  assert.equal(await offline.evaluate(()=>state.sources.length),1042);
  await offline.locator('[data-view="studies"]').click();assert.equal(await offline.locator('#studyTableBody tr').count(),30);
  assert.deepEqual(errors,[]);
  await fs.writeFile(`${out}/browser_validation.json`,JSON.stringify({status:'PASS',mode:live?'canonical':'staged',source_count:1042,study_count:30,project_count:17,filters:true,source_links:true,export:true,mobile:true,dark_theme:true,offline_fallback:true,page_errors:errors},null,2));
  console.log('PASS: registry navigation, filters, detail/source links, CSV, mobile, dark theme and offline fallback.');
} finally {if(browser)await browser.close();await new Promise(r=>server.close(r));}
