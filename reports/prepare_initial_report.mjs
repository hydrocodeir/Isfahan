import fs from 'node:fs';
import vm from 'node:vm';
import path from 'node:path';
import {createRequire} from 'node:module';
const require = createRequire('C:/Users/psh2610/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/package.json');
const {chromium} = require('playwright');
const out = path.resolve('reports/initial_progress_14050719');
fs.mkdirSync(out,{recursive:true});
const data = JSON.parse(fs.readFileSync('data.json','utf8'));
const js=fs.readFileSync('app.js','utf8');
const code=js.slice(js.indexOf('const $ ='),js.indexOf('async function boot()'));
const sandbox={console,Intl,URL}; vm.createContext(sandbox); vm.runInContext(code+'\nthis.processData=preprocess;',sandbox);
const sources=sandbox.processData(data).sources;
const count=(items,fn)=>Object.entries(items.reduce((a,s)=>{let k=fn(s)??'ثبت نشده';a[k]=(a[k]||0)+1;return a;},{})).sort((a,b)=>b[1]-a[1]);
const stats={total:sources.length,meta:data.meta,collections:Object.fromEntries(Object.entries(data.collections).map(([k,v])=>[k,v.length])),groups:count(sources,s=>s._group),language:count(sources,s=>s.Language),reliability:count(sources,s=>s.Reliability),primary:count(sources,s=>s.Primary_or_Secondary),fulltext:count(sources,s=>s.Full_Text),pdfstatus:count(sources,s=>s.PDF_Status),stances:count(sources,s=>s._stanceGroup),years:count(sources,s=>s._year),projects:count(sources.flatMap(s=>s._projectTags.map(t=>({tag:t}))),s=>s.tag),provinces:count(sources.flatMap(s=>s._provinceTags.map(t=>({tag:t}))),s=>s.tag),publishers:count(sources,s=>s.Publisher),fields:Object.fromEntries(['Date_Gregorian','Date_Persian','Year','DOI','URL','Summary','Key_Claim','Quote','Province','Organization','Author','PDF_URL','Local_PDF','SHA256'].map(k=>[k,sources.filter(s=>s[k]&&String(s[k]).trim()).length])),queries:data.searchLog.length,queryDB:count(data.searchLog,s=>s['Database / Search Engine']||s.Database||s['Database/Search Engine']),queryLang:count(data.searchLog,s=>s.Language),queryDates:count(data.searchLog,s=>s['Search Date']||s.Search_Date),studies:count(data.transferResearch.studies,s=>s.subcategory),cooperation:count(data.transferResearch.studies,s=>s.cooperation_type),studyProjects:data.transferProjects.map(p=>[p.id,p.name_fa,data.transferResearch.studies.filter(s=>s.project_ids.includes(p.id)).length]),changes:data.changeLog.filter(c=>c.Date>='2026-09-23'&&c.Date<='2026-10-11'),idUnique:new Set(sources.map(s=>s.Source_ID)).size};
fs.writeFileSync(path.join(out,'statistics.json'),JSON.stringify(stats,null,2));
let browser;
try {browser=await chromium.launch({channel:'msedge',headless:true});} catch(e) {browser=await chromium.launch({channel:'chrome',headless:true});}
const page=await browser.newPage({viewport:{width:1480,height:1050},deviceScaleFactor:1.5});
const errors=[];page.on('pageerror',e=>errors.push(e.message));
let origin='https://hydrocodeir.github.io/Isfahan/';
try {await page.goto(origin,{waitUntil:'domcontentloaded',timeout:45000}); await page.waitForFunction(()=>typeof state!=='undefined'&&state.data,{timeout:30000});}
catch(e){origin='file:///'+path.resolve('index.html').replaceAll('\\','/'); await page.goto(origin,{waitUntil:'domcontentloaded',timeout:30000});await page.waitForFunction(()=>typeof state!=='undefined'&&state.data);}
await page.evaluate(()=>{localStorage.setItem('theme','light');applyTheme('light');});
await page.evaluate(()=>document.fonts.ready);
await page.waitForTimeout(1500);
for(const view of ['overview','sources','timeline','legal','projects','studies','research']){
  if(view==='studies') await page.setViewportSize({width:1920,height:1050});
  await page.locator(`[data-view="${view}"]`).click();await page.waitForTimeout(400);
  await page.screenshot({path:path.join(out,`dashboard_${view}.png`),fullPage:false});
  if(view==='overview') await page.screenshot({path:path.join(out,'dashboard_overview_full.png'),fullPage:true});
}
await page.setViewportSize({width:1480,height:1050});
await page.locator('[data-view="sources"]').click();
await page.evaluate(()=>openSource('S099'));await page.waitForTimeout(300);
await page.screenshot({path:path.join(out,'dashboard_source_details.png')});
const live=await page.evaluate(()=>({sources:state.sources.length,meta:state.data.meta,studies:state.data.transferResearch?.studies?.length,projects:state.data.transferProjects?.length}));
const liveData=await page.evaluate(()=>state.data);
fs.writeFileSync(path.join(out,'live_data.json'),JSON.stringify(liveData,null,2));
console.log('LIVE_LOCAL_MATCH',JSON.stringify(liveData)===JSON.stringify(data));
fs.writeFileSync(path.join(out,'browser_capture.json'),JSON.stringify({origin,live,errors},null,2));
console.log(JSON.stringify({stats:{total:stats.total,groups:stats.groups,projects:stats.projects.slice(0,12),queries:stats.queries,studies:stats.studies},browser:{origin,live,errors}},null,2));
await browser.close();
