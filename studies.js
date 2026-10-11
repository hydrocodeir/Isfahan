/* The registry uses canonical source IDs from data.json, including offline mode. */
function registryProjects() { return state.data.transferProjects || []; }
function registryStudies() { return state.data.transferResearch?.studies || []; }
function studyProjectNames(study) {
  return registryProjects().filter(p => study.project_ids.includes(p.id)).map(p => p.name_fa);
}
function studyProvinces(study) {
  return uniq(registryProjects().filter(p => study.project_ids.includes(p.id)).flatMap(p => [...(p.provinces || []), ...(p.downstream_or_shared || [])]));
}
function studyMatches(study) {
  const q = norm($("#studySearch").value);
  const project = $("#studyProject").value, category = $("#studyCategory").value;
  const province = $("#studyProvince").value, cooperation = $("#studyCooperation").value;
  return (!q || norm([...Object.values(study), ...studyProjectNames(study)].join(" ")).includes(q))
    && (!project || (project === "unlinked" ? !study.project_ids.length : study.project_ids.includes(project)))
    && (!category || study.subcategory === category)
    && (!province || studyProvinces(study).includes(province))
    && (!cooperation || study.cooperation_type === cooperation);
}
function populateStudyFilters() {
  selectOptions($("#studyCategory"), uniq(registryStudies().map(s => s.subcategory)), "همه زیرگروه‌ها");
  $("#studyProject").innerHTML = '<option value="">همه طرح‌ها</option>' + registryProjects().map(p => `<option value="${esc(p.id)}">${esc(p.name_fa)}</option>`).join("") + '<option value="unlinked">پژوهش عمومی / ارتباط با طرح مشخص نشده</option>';
  selectOptions($("#studyProvince"), uniq(registryProjects().flatMap(p => [...(p.provinces || []), ...(p.downstream_or_shared || [])])), "همه استان‌ها");
}
function registrySourceButtons(ids) {
  return ids.map(id => `<button type="button" class="text-btn registry-source" data-registry-source="${esc(id)}" aria-label="جزئیات منبع ${esc(id)}">${esc(id)}</button>`).join(" ");
}
function bindRegistrySources(root) {
  $$("[data-registry-source]", root).forEach(b => b.addEventListener("click", () => openSource(b.dataset.registrySource)));
}
function renderStudies() {
  const rows = registryStudies().filter(studyMatches);
  $("#studyCountingNote").textContent = state.data.transferResearch?.counting_note || "";
  $("#studyResultCount").textContent = `${fmt(rows.length)} از ${fmt(registryStudies().length)} رکورد`;
  $("#studyTableBody").innerHTML = rows.length ? rows.map(s => `<tr>
    <td class="title-cell"><span class="source-id">${esc(s.id)}</span><button type="button" class="study-title" data-study="${esc(s.id)}">${esc(s.title_fa)}</button></td>
    <td>${esc(s.subcategory)}</td><td>${esc(studyProjectNames(s).join("؛ ") || "عمومی / ارتباط مشخص نشده")}</td>
    <td>${esc(s.performer)}</td><td>${esc(s.commissioner_or_funder)}</td><td>${esc(val(s.period,"نامشخص"))}</td>
    <td>${esc(s.cooperation)}</td><td>${registrySourceButtons(s.source_ids)}</td>
  </tr>`).join("") : '<tr><td colspan="8"><div class="empty-state">مطالعه‌ای با این فیلترها پیدا نشد.</div></td></tr>';
  $$("[data-study]", $("#studyTableBody")).forEach(b => b.addEventListener("click", () => openStudy(b.dataset.study)));
  bindRegistrySources($("#studyTableBody"));
  const leads = state.data.transferResearch?.leads || [];
  $("#studyLeads").innerHTML = leads.map(l => `<p>${Object.entries(l).filter(([key]) => !["id", "source_ids"].includes(key)).map(([,value]) => esc(Array.isArray(value) ? value.join("؛ ") : value)).join(" · ")}</p>`).join("");
}
function openStudy(id) {
  const s = registryStudies().find(s => s.id === id); if (!s) return;
  const facts = [["زیرگروه",s.subcategory],["طرح‌های مرتبط",studyProjectNames(s).join("؛ ") || "عمومی / ارتباط مشخص نشده"],
    ["مجری / مشاور",s.performer],["کارفرما / حامی",s.commissioner_or_funder],["دوره مستند",val(s.period,"نامشخص")],["همکاری",s.cooperation]];
  $("#modalContent").innerHTML = `<div class="modal-id">${esc(s.id)}</div><h2 id="modalTitle">${esc(s.title_fa)}</h2>
    <div class="modal-grid">${facts.map(([label,value]) => `<div class="modal-fact"><span>${esc(label)}</span><strong>${esc(value)}</strong></div>`).join("")}</div>
    <div class="content-block"><h4>موضوع و حدود مطالعه</h4><p>${esc(s.scope)}</p></div>
    <div class="content-block"><h4>نوع شاهد و میزان تأیید</h4><p>${esc(s.evidence)}</p></div>
    <div class="content-block"><h4>منابع مستند</h4>${registrySourceButtons(s.source_ids)}
      ${(state.data.transferResearch?.source_evidence || []).filter(e => s.source_ids.includes(e.source_id)).map(e => `<p><a href="${safeUrl(e.url)}" target="_blank" rel="noopener">${esc(e.title)}</a><br><span class="title-sub">${esc(e.access)}</span></p>`).join("")}</div>`;
  bindRegistrySources($("#modalContent"));
  $("#sourceModal").classList.add("open"); $("#sourceModal").setAttribute("aria-hidden","false"); document.body.style.overflow = "hidden";
}
function renderTransferProjectCatalog(q) {
  const rows = registryProjects().filter(p => !q || norm([p.name_fa,p.name_en,p.origin,p.destination,...p.provinces].join(" ")).includes(q));
  $("#transferProjectCatalog").innerHTML = rows.map(p => `<details class="panel transfer-project m3-card">
    <summary><strong>${esc(p.name_fa)}</strong><span class="title-sub">مبدأ: ${esc(p.origin)}؛ مقصد: ${esc(p.destination)}</span></summary>
    <dl class="registry-facts"><dt>مبدأ</dt><dd>${esc(p.origin)}</dd><dt>مقصد</dt><dd>${esc(p.destination)}</dd>
    <dt>استان‌های طرح</dt><dd>${esc(p.provinces.join("؛ "))}</dd><dt>پایین‌دست / حوضه مشترک</dt><dd>${esc(Array.isArray(p.downstream_or_shared) ? p.downstream_or_shared.join("؛ ") : val(p.downstream_or_shared))}</dd>
    <dt>نوع انتقال</dt><dd>${esc(p.transfer_type)}</dd><dt>شاهد وضعیت</dt><dd>${esc(p.status_evidence)}</dd><dt>تاریخ شاهد</dt><dd>${esc(p.status_as_of || "نامشخص")}</dd></dl>
    <div class="registry-actions">${registrySourceButtons(p.source_ids)}<button type="button" class="text-btn" data-project-studies="${esc(p.id)}">مطالعات این طرح (${fmt(registryStudies().filter(s => s.project_ids.includes(p.id)).length)})</button></div>
  </details>`).join("") || '<div class="empty-state">طرحی با این عبارت پیدا نشد.</div>';
  bindRegistrySources($("#transferProjectCatalog"));
  $$("[data-project-studies]", $("#transferProjectCatalog")).forEach(b => b.addEventListener("click", () => {
    ["studySearch", "studyCategory", "studyProvince", "studyCooperation"].forEach(id => $("#" + id).value = "");
    $("#studyProject").value = b.dataset.projectStudies; renderStudies(); switchView("studies");
  }));
}
function exportStudies() {
  const cols = [["id","شناسه"],["title_fa","عنوان مطالعه"],["subcategory","زیرگروه"],["project_ids","شناسه طرح‌ها"],["performer","مجری / مشاور"],["commissioner_or_funder","کارفرما / حامی"],["period","دوره"],["cooperation","همکاری"],["scope","موضوع و حدود مطالعه"],["evidence","نوع شاهد"],["source_ids","شناسه منابع"]];
  const sources = new Map(state.sources.map(s => [s.Source_ID,s]));
  const q = value => { const text = String(value ?? ""); return '"' + (/^[=+@-]/.test(text) ? "'" : "") + text.replace(/"/g,'""') + '"'; };
  const rows = registryStudies().filter(studyMatches);
  const csv = [[...cols.map(c => q(c[1])),q("پیوند منابع")].join(","), ...rows.map(s => [...cols.map(([key]) => q(Array.isArray(s[key]) ? s[key].join("؛ ") : s[key])),q(s.source_ids.map(id => sources.get(id)?.URL || "").join("\n"))].join(","))].join("\r\n");
  downloadBlob(new Blob(["\ufeff",csv],{type:"text/csv;charset=utf-8"}),"water-transfer-studies.csv"); showToast(`${fmt(rows.length)} رکورد مطالعه خروجی گرفته شد`);
}
