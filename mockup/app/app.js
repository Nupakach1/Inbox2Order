/* Inbox2Order - giao diện demo. Dữ liệu: data.js do build_mockup.py sinh từ data/ và kết quả luồng xử lý.
   Không có backend: mọi thao tác (sửa, xác nhận, từ chối, lưu bí danh) chỉ đổi dữ liệu trong trình duyệt. */
const D = window.I2O;
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

const ORDER_ST = { draft: "Đơn nháp", needs_review: "Cần kiểm tra", waiting_customer: "Chờ khách bổ sung", confirmed: "Đã xác nhận", rejected: "Đã từ chối" };
const ORDER_CLR = { draft: "bg-sky-50 text-sky-700 ring-sky-200", needs_review: "bg-amber-50 text-amber-800 ring-amber-200", waiting_customer: "bg-violet-50 text-violet-700 ring-violet-200", confirmed: "bg-emerald-50 text-emerald-700 ring-emerald-200", rejected: "bg-rose-50 text-rose-700 ring-rose-200" };
const ORDER_DOT = { draft: "bg-sky-500", needs_review: "bg-amber-500", waiting_customer: "bg-violet-500", confirmed: "bg-emerald-500", rejected: "bg-rose-500" };
const EMAIL_ST = { received: "Mới nhận", classified: "Đã phân loại", drafted: "Đã tạo đơn nháp", forwarded: "Đã chuyển người phụ trách" };
const LABEL = { new_customer: "Khách mới", price_inquiry: "Hỏi giá", complaint: "Khiếu nại", other: "Khác", possible_duplicate: "Có thể trùng", has_attachment: "Có đính kèm" };
const CAT = { new_order: "Đặt hàng mới", modify_order: "Sửa đơn", price_inquiry: "Hỏi giá", complaint: "Khiếu nại", other: "Khác" };
const ROLE = { sales_admin: "Sales Admin", sales_manager: "Trưởng phòng kinh doanh", system_admin: "Quản trị hệ thống" };
const ICON = {
  inbox: '<path d="M3 13h5l1.5 3h5L16 13h5"/><path d="M5 5h14l2 8v6H3v-6z"/>',
  box: '<path d="M3 7l9-4 9 4-9 4z"/><path d="M3 7v10l9 4 9-4V7"/><path d="M12 11v10"/>',
  chart: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
  back: '<path d="M15 18l-6-6 6-6"/>',
  check: '<path d="M5 12l5 5L20 7"/>',
  x: '<path d="M6 6l12 12M18 6L6 18"/>',
  mail: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  alert: '<path d="M12 3l10 18H2z"/><path d="M12 10v4M12 17.5v.5"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/>',
  lock: '<rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
  doc: '<path d="M6 3h9l4 4v14H6z"/><path d="M14 3v5h5M9 13h7M9 17h5"/>',
  forward: '<path d="M15 5l6 6-6 6"/><path d="M21 11H9a6 6 0 0 0-6 6v2"/>',
  history: '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5M12 7v5l3 2"/>',
};
const ico = (n, cls = "ico") => `<svg viewBox="0 0 24 24" class="${cls}" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${ICON[n]}</svg>`;
const initials = (name) => (name || "").split(" ").filter(Boolean).slice(-2).map((w) => w[0]).join("").toUpperCase();
function toast(msg, kind = "ok") {
  const clr = kind === "ok" ? "bg-slate-900 text-white" : "bg-rose-600 text-white";
  const el = document.createElement("div");
  el.className = `toast-in ${clr} px-4 py-2.5 rounded-lg shadow-lg text-sm flex items-center gap-2`;
  el.innerHTML = `${ico(kind === "ok" ? "check" : "alert")}<span>${msg}</span>`;
  $("#toast").appendChild(el); setTimeout(() => el.remove(), 3200);
}
const DAYS = ["Chủ nhật", "Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy"];

const state = { user: D.users.find((u) => u.username === "huong.nt"), day: "2026-11-02", filter: { status: "", customer: "", label: "" }, timing: loadTiming() };
const emailById = Object.fromEntries(D.emails.map((e) => [e.email_id, e]));
const orderByEmail = Object.fromEntries(D.orders.map((o) => [o.email_id, o]));
const userName = (u) => (D.users.find((x) => x.username === u) || {}).full_name || "";

function loadTiming() { try { return JSON.parse(localStorage.getItem("i2o_timing") || "[]"); } catch (e) { return []; } }
function saveTiming() { try { localStorage.setItem("i2o_timing", JSON.stringify(state.timing)); } catch (e) { /* trình duyệt chặn lưu */ } }

const fmtTime = (s) => s.slice(11, 16);
const fmtDate = (s) => `${s.slice(8, 10)}/${s.slice(5, 7)}`;
const fmtDT = (s) => `${fmtTime(s)} ${fmtDate(s)}`;
const vnDate = (d) => `${d.slice(8, 10)}/${d.slice(5, 7)}/${d.slice(0, 4)} (${DAYS[new Date(d + "T12:00").getDay()]})`;
const dayName = (d) => DAYS[new Date(d + "T12:00").getDay()];
const num = (x) => (x === null || x === undefined ? "" : Number(x).toLocaleString("vi-VN"));
const badge = (st) => `<span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium ring-1 ring-inset whitespace-nowrap ${ORDER_CLR[st]}"><span class="w-1.5 h-1.5 rounded-full ${ORDER_DOT[st]}"></span>${ORDER_ST[st]}</span>`;
const isManager = () => state.user.role === "sales_manager";
const isAdmin = () => state.user.role === "sales_admin";

/* ---------- quy tắc kiểm tra dòng hàng, đơn (giống view v_order_items_review và trigger kiểm tra trường bắt buộc) ---------- */
function itemFlags(it) {
  const p = D.products[it.sku];
  const f = [];
  if (it.match_status === "suggested") f.push(it.match_score >= 90 ? `Nhiều mã cùng điểm ${it.match_score}: chọn đúng mã` : `Gợi ý, chưa chắc (điểm ${it.match_score})`);
  if (it.match_status === "unmatched") f.push(`Không khớp (điểm ${it.match_score}): bắt buộc chọn mã`);
  if (it.qty_raw === null) f.push("Email không nêu số lượng");
  else if (it.sku && it.qty_base === null) f.push(`Đơn vị “${it.unit_raw}” không có trong quy cách`);
  if (p && it.qty_base !== null && it.qty_base > Number(p.max_normal_qty)) f.push(`Có thể nhập nhầm: ${num(it.qty_base)} ${p.unit} > ngưỡng ${p.max_normal_qty}`);
  return f;
}
function blockers(o) {
  const b = [];
  if (!o.customer_id) b.push("Chưa có khách hàng");
  if (!o.items.length) b.push("Đơn chưa có dòng hàng");
  o.items.forEach((it) => {
    if (!it.sku) b.push(`Dòng ${it.line_no}: chưa có mã hàng`);
    if (it.qty_base === null) b.push(`Dòng ${it.line_no}: chưa có số lượng`);
  });
  return b;
}
const reviewCount = (o) => o.items.filter((it) => itemFlags(it).length).length + (o.address_needs_review ? 1 : 0) + (o.date_needs_review ? 1 : 0);

/* ---------- khung chung ---------- */
function nav(active) {
  const items = [["hop-thu", "Hộp thư", "inbox"], ["danh-muc", "Danh mục SKU", "box"], ["bao-cao", "Dashboard KPI", "chart"]];
  $("#nav").innerHTML = items.map(([id, t, ic]) =>
    `<a href="#${id}" class="flex items-center gap-2 px-3 py-2 rounded-lg whitespace-nowrap font-medium ${active === id ? "bg-indigo-50 text-indigo-700" : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"}">${ico(ic)}${t}</a>`).join("");
  $("#role").innerHTML = D.users.map((u) => `<option value="${u.username}" ${u.username === state.user.username ? "selected" : ""}>${u.full_name} · ${ROLE[u.role]}</option>`).join("");
  $("#avatar").textContent = initials(state.user.full_name);
}
$("#role").onchange = (e) => { state.user = D.users.find((u) => u.username === e.target.value); route(); };

function card(title, body, extra = "", icon = "") {
  return `<section class="bg-white rounded-xl border border-slate-200 shadow-sm ${extra}">
    ${title ? `<div class="px-5 py-3 border-b border-slate-100 font-semibold text-slate-800 flex items-center gap-2">${icon ? `<span class="text-slate-400">${ico(icon)}</span>` : ""}${title}</div>` : ""}<div class="p-5">${body}</div></section>`;
}
const pageHead = (title, sub, right = "") => `<div class="flex items-end gap-4 mb-5"><div><h1 class="text-2xl font-semibold text-slate-900">${title}</h1>
  <div class="text-slate-500 mt-0.5">${sub}</div></div><div class="ml-auto flex gap-2 items-center">${right}</div></div>`;
const TH = 'class="text-left text-xs font-medium text-slate-500 uppercase tracking-wide"';
const inputCls = "border border-slate-300 rounded-lg px-2.5 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-200";

/* ---------- Hộp thư chờ xử lý ---------- */
function mh01() {
  nav("hop-thu");
  const days = [...new Set(D.orders.map((o) => o.ready_at.slice(0, 10)))].sort();
  const f = state.filter;
  let list = D.orders.filter((o) => o.ready_at.slice(0, 10) === state.day);
  const counts = Object.fromEntries(Object.keys(ORDER_ST).map((k) => [k, list.filter((o) => o.status === k).length]));
  if (f.status) list = list.filter((o) => o.status === f.status);
  if (f.customer) list = list.filter((o) => o.customer_id === f.customer);
  list.sort((a, b) => a.deadline.localeCompare(b.deadline) || emailById[a.email_id].received_at.localeCompare(emailById[b.email_id].received_at));
  const fwd = D.emails.filter((e) => e.status === "forwarded" && e.received_at.slice(0, 10) === state.day && (!f.label || e.label === f.label));
  const late = D.orders.filter((o) => emailById[o.email_id].received_at.slice(0, 10) === state.day && +emailById[o.email_id].received_at.slice(11, 13) < 17
    && !["confirmed", "rejected"].includes(o.status));
  const custs = [...new Set(D.orders.filter((o) => o.ready_at.slice(0, 10) === state.day).map((o) => o.customer_id))].sort();

  const chips = Object.entries(counts).map(([k, n]) =>
    `<button data-st="${k}" class="st px-4 py-3 rounded-xl border text-left shadow-sm transition ${f.status === k ? "border-indigo-400 ring-2 ring-indigo-100 bg-white" : "border-slate-200 bg-white hover:border-slate-300"}">
      <div class="flex items-center gap-2 text-xs text-slate-500"><span class="w-2 h-2 rounded-full ${ORDER_DOT[k]}"></span>${ORDER_ST[k]}</div><div class="text-2xl font-semibold tabnum mt-1 text-slate-900">${n}</div></button>`).join("");
  const rows = list.map((o) => {
    const e = emailById[o.email_id], c = D.customers[o.customer_id] || {};
    const rc = reviewCount(o);
    return `<tr class="border-t border-slate-100 hover:bg-indigo-50/40 cursor-pointer" onclick="location.hash='#don/${o.email_id}'">
      <td class="py-2.5 px-3 tabnum whitespace-nowrap font-medium">${fmtDT(o.deadline)}</td>
      <td class="px-3 font-mono text-xs text-slate-500">${o.email_id}</td>
      <td class="px-3"><div class="flex items-center gap-2.5"><span class="w-8 h-8 rounded-full bg-slate-100 text-slate-600 text-xs font-semibold flex items-center justify-center flex-none">${initials(c.name)}</span>
        <div><div class="font-medium text-slate-900">${esc(c.name)}</div><div class="text-xs text-slate-500">${o.customer_id}</div></div></div></td>
      <td class="px-3">${esc(e.subject || "(không có tiêu đề)")}${e.received_at.slice(11, 13) >= "17" ? ' <span class="text-xs text-slate-500">· nhận sau 17h00</span>' : ""}</td>
      <td class="px-3 tabnum whitespace-nowrap">${fmtDT(e.received_at)}</td>
      <td class="px-3 text-center tabnum">${o.items.length}</td>
      <td class="px-3 text-center">${rc ? `<span class="px-2 py-0.5 rounded-full bg-amber-50 text-amber-800 ring-1 ring-inset ring-amber-200 text-xs font-medium whitespace-nowrap">${rc} trường</span>` : '<span class="text-xs text-slate-300">-</span>'}</td>
      <td class="px-3">${badge(o.status)}</td>
    </tr>`;
  }).join("") || `<tr><td colspan="8" class="py-10 text-center text-slate-400">${ico("inbox", "w-8 h-8 mx-auto mb-2")}Không có đơn nào khớp bộ lọc.</td></tr>`;
  const fwdRows = fwd.map((e) => `<tr class="border-t border-slate-100">
      <td class="py-2.5 px-3 font-mono text-xs text-slate-500">${e.email_id}</td><td class="px-3">${esc(e.from_email)}</td><td class="px-3">${esc(e.subject)}</td>
      <td class="px-3 tabnum">${fmtDT(e.received_at)}</td>
      <td class="px-3"><span class="px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 text-xs font-medium whitespace-nowrap">${LABEL[e.label]}</span></td>
      <td class="px-3">${userName(e.forwarded_to)}</td><td class="px-3 text-xs text-slate-500">${esc(e.note || "")}</td></tr>`).join("")
    || `<tr><td colspan="7" class="py-6 text-center text-slate-400">Không có email nào được chuyển trong ngày.</td></tr>`;

  $("#app").innerHTML = `
    ${pageHead("Hộp thư chờ xử lý", `Đơn nháp đưa vào danh sách duyệt ngày ${dayName(state.day)} ${fmtDate(state.day)}/2026, sắp theo hạn xác nhận`,
      `<label class="text-xs text-slate-500">Ngày làm việc</label>
        <select id="day" class="${inputCls}">${days.map((d) => `<option value="${d}" ${d === state.day ? "selected" : ""}>${dayName(d)} ${fmtDate(d)}</option>`).join("")}</select>
        <select id="fcust" class="${inputCls}"><option value="">Tất cả khách hàng</option>${custs.map((c) => `<option value="${c}" ${c === f.customer ? "selected" : ""}>${c} · ${esc(D.customers[c].name)}</option>`).join("")}</select>`)}
    ${late.length ? `<div class="mb-5 px-4 py-3 rounded-xl bg-orange-50 border border-orange-200 text-orange-900 flex items-center gap-3">${ico("clock", "w-5 h-5 text-orange-500")}
      <div><b>Cảnh báo 16h30:</b> còn ${late.length} đơn nhận trước 17h00 ngày ${fmtDate(state.day)} chưa xác nhận hoặc từ chối. ${isManager() ? "Danh sách đã gửi cho Trưởng phòng kinh doanh để điều phối." : ""}</div></div>` : ""}
    <div class="grid grid-cols-5 gap-3 mb-5">${chips}</div>
    ${card(`Đơn chờ duyệt <span class="font-normal text-slate-400">${list.length}</span>${f.status ? `<span class="ml-2 text-xs font-normal px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700">${ORDER_ST[f.status]}</span> <a href="#" id="clr" class="text-indigo-600 text-xs font-normal hover:underline">Bỏ lọc</a>` : ""}`,
      `<table class="w-full"><thead><tr>
        <th ${TH} style="padding:0 .75rem .6rem">Hạn xác nhận</th><th ${TH} style="padding:0 .75rem .6rem">Mã email</th><th ${TH} style="padding:0 .75rem .6rem">Khách hàng</th><th ${TH} style="padding:0 .75rem .6rem">Tiêu đề</th><th ${TH} style="padding:0 .75rem .6rem">Nhận lúc</th>
        <th ${TH} style="padding:0 .75rem .6rem;text-align:center">Số dòng</th><th ${TH} style="padding:0 .75rem .6rem;text-align:center">Cần kiểm tra</th><th ${TH} style="padding:0 .75rem .6rem">Trạng thái</th></tr></thead><tbody>${rows}</tbody></table>`, "mb-5", "inbox")}
    ${card(`Email đã chuyển người phụ trách
      <select id="flabel" class="ml-auto ${inputCls} text-xs font-normal"><option value="">Tất cả nhãn</option>${Object.entries(LABEL).map(([k, v]) => `<option value="${k}" ${k === f.label ? "selected" : ""}>${v}</option>`).join("")}</select>`,
      `<table class="w-full"><thead><tr><th ${TH} style="padding:0 .75rem .6rem">Mã email</th><th ${TH} style="padding:0 .75rem .6rem">Người gửi</th><th ${TH} style="padding:0 .75rem .6rem">Tiêu đề</th>
        <th ${TH} style="padding:0 .75rem .6rem">Nhận lúc</th><th ${TH} style="padding:0 .75rem .6rem">Nhãn</th><th ${TH} style="padding:0 .75rem .6rem">Người nhận</th><th ${TH} style="padding:0 .75rem .6rem">Ghi chú</th></tr></thead><tbody>${fwdRows}</tbody></table>`, "", "forward")}`;
  $("#day").onchange = (e) => { state.day = e.target.value; state.filter.customer = ""; mh01(); };
  $("#fcust").onchange = (e) => { state.filter.customer = e.target.value; mh01(); };
  $("#flabel").onchange = (e) => { state.filter.label = e.target.value; mh01(); };
  document.querySelectorAll(".st").forEach((b) => (b.onclick = () => { state.filter.status = state.filter.status === b.dataset.st ? "" : b.dataset.st; mh01(); }));
  const clr = $("#clr"); if (clr) clr.onclick = (ev) => { ev.preventDefault(); state.filter.status = ""; mh01(); };
}

/* ---------- Chi tiết đơn nháp ---------- */
function addLog(o, field, oldV, newV, lineNo) {
  D.logs.push({ order_id: o.order_id, line_no: lineNo ?? null, field_name: field, old_value: oldV === null ? null : String(oldV),
    new_value: newV === null ? null : String(newV), edited_by: state.user.username, edited_at: new Date().toISOString() });
}
function toBase(sku, qty, unit) {
  const p = D.products[sku]; if (!p || qty === null) return null;
  const n = (s) => (s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/đ/g, "d").toLowerCase().trim();
  const ab = { h: "hop", th: "thung", l: "loc", c: "cai" };
  const u = ab[n(unit)] || n(unit);
  if (!unit || u === n(p.unit)) return qty;
  if (p.pack_unit && u === n(p.pack_unit)) return qty * Number(p.pack_size);
  return null;
}

function mh02(emailId) {
  nav("hop-thu");
  const o = orderByEmail[emailId], e = emailById[emailId];
  if (!o) { $("#app").innerHTML = card("", `Email ${esc(emailId)} không tạo đơn nháp.`); return; }
  const decided = ["confirmed", "rejected"].includes(o.status);
  if (isAdmin() && !decided && !o._opened) { o._opened = Date.now(); o.locked_by = state.user.username; }
  const c = D.customers[o.customer_id] || {};
  const addrs = [c.default_address, ...new Set(D.orders.filter((x) => x.customer_id === o.customer_id && x.ship_address !== c.default_address).map((x) => x.ship_address))];
  const ro = !isAdmin() || decided;
  const block = blockers(o);
  const logs = D.logs.filter((l) => l.order_id === o.order_id);
  const mod = D.emails.filter((x) => x.modifies_email_id === emailId);

  const itemRows = o.items.map((it, idx) => {
    const p = D.products[it.sku] || {}, flags = itemFlags(it);
    const opts = [...new Set([it.sku, ...(it.suggestions || []).map((s) => s[0])].filter(Boolean))];
    const sel = ro ? `<span class="font-mono">${it.sku || "-"}</span>` :
      `<select data-i="${idx}" class="sku border border-slate-300 rounded-lg px-1.5 py-1 w-full font-mono text-xs bg-white">
        ${it.sku ? "" : '<option value="">Chọn mã hàng</option>'}
        ${opts.map((s) => { const sc = (it.suggestions || []).find((x) => x[0] === s); return `<option value="${s}" ${s === it.sku ? "selected" : ""}>${s} · ${esc(D.products[s].name)}${sc ? ` (${sc[1]})` : ""}</option>`; }).join("")}
        <option value="__other">Chọn mã khác trong danh mục…</option></select>`;
    return `<tr class="border-t border-slate-100 ${flags.length ? "review" : ""}">
      <td class="py-2 px-2 text-center text-slate-500">${it.line_no}</td>
      <td class="px-2"><div>${esc(it.product_text)}</div></td>
      <td class="px-2 text-right tabnum">${it.qty_raw ?? '<span class="text-amber-700 font-medium">?</span>'}</td>
      <td class="px-2">${esc(it.unit_raw || "")}</td>
      <td class="px-2 w-64">${sel}<div class="text-xs text-slate-500 mt-0.5">${esc(p.name || "")}</div></td>
      <td class="px-2 text-right tabnum whitespace-nowrap">${ro ? num(it.qty_base) : `<input data-i="${idx}" class="qb border border-slate-300 rounded-lg w-20 px-1.5 py-1 text-right" value="${it.qty_base ?? ""}">`} <span class="text-xs text-slate-500">${p.unit || ""}</span></td>
      <td class="px-2 text-center tabnum">${it.match_score}</td>
      <td class="px-2 text-xs text-amber-800">${flags.map(esc).join("<br>")}</td></tr>`;
  }).join("") || `<tr class="review"><td colspan="8" class="py-4 px-3 text-amber-800">Email không có dòng hàng cụ thể. Hãy đề nghị khách bổ sung hoặc nhập tay.</td></tr>`;

  const sap = o.items.map((it, i) => `<tr class="border-t border-slate-100"><td class="py-1 px-2 tabnum">${(i + 1) * 10}</td><td class="px-2 font-mono">${it.sku || "-"}</td>
      <td class="px-2 text-right tabnum">${num(it.qty_base)}</td><td class="px-2">${(D.products[it.sku] || {}).unit || ""}</td></tr>`).join("");

  $("#app").innerHTML = `
    <a href="#hop-thu" class="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-indigo-600 mb-2">${ico("back")}Hộp thư</a>
    <div class="flex items-center gap-3 mb-5">
      <h1 class="text-2xl font-semibold text-slate-900">Đơn nháp từ email ${o.email_id}</h1>${badge(o.status)}
      <span class="inline-flex items-center gap-1.5 text-slate-500">${ico("clock")}Hạn xác nhận ${fmtDT(o.deadline)}</span>
      ${o.locked_by && !decided ? `<span class="ml-auto inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full bg-slate-100 text-slate-600">${ico("lock")}Đang xử lý: ${userName(o.locked_by)}</span>` : ""}
    </div>
    ${isManager() ? `<div class="mb-5 px-4 py-3 rounded-xl bg-slate-100 border border-slate-200 text-slate-700 flex items-center gap-2">${ico("lock", "w-5 h-5 text-slate-400")}Trưởng phòng kinh doanh chỉ xem đơn; chỉ Sales Admin được sửa, xác nhận hoặc từ chối.</div>` : ""}
    <div class="grid grid-cols-12 gap-4">
      <div class="col-span-5 space-y-4">
        ${card("Email gốc", `
          <dl class="grid grid-cols-[90px_1fr] gap-y-1 text-xs mb-3">
            <dt class="text-slate-500">Từ</dt><dd>${esc(e.from_name)} &lt;${esc(e.from_email)}&gt;</dd>
            <dt class="text-slate-500">Đến</dt><dd>${esc(e.to_email)}</dd>
            <dt class="text-slate-500">Tiêu đề</dt><dd>${esc(e.subject || "(không có)")}</dd>
            <dt class="text-slate-500">Nhận lúc</dt><dd>${dayName(e.received_at.slice(0, 10))} ${fmtDT(e.received_at)}/2026</dd>
            <dt class="text-slate-500">Phân loại</dt><dd>${CAT[e.category]} · ${EMAIL_ST[e.status]}</dd></dl>
          <pre class="whitespace-pre-wrap font-sans bg-slate-50 border border-slate-200 rounded-lg p-3 leading-relaxed">${esc(e.body)}</pre>
          ${mod.length ? `<div class="mt-3 text-xs px-3 py-2 rounded-lg bg-sky-50 border border-sky-200">Đơn đã được cập nhật theo email sửa đơn ${mod.map((m) => `<b>${m.email_id}</b> (${fmtDT(m.received_at)})`).join(", ")}.</div>` : ""}
          <details class="mt-3 text-xs"><summary class="cursor-pointer text-slate-600">Nội dung đã gửi cho mô hình AI (đã che thông tin cá nhân)</summary>
            <pre class="whitespace-pre-wrap font-sans bg-slate-50 border border-slate-200 rounded-lg p-2 mt-2">${esc(e.masked_input)}</pre>
            <div class="text-slate-500 mt-1">Đã che: ${e.mask_counts.phone} số điện thoại, ${e.mask_counts.bank_account} số tài khoản, ${e.mask_counts.signature} chữ ký.</div></details>`, "", "mail")}
        ${card("Xem trước Sales Order SAP", `
          <dl class="grid grid-cols-[150px_1fr] gap-y-1 text-xs mb-2">
            <dt class="text-slate-500">Order Type, Sales Area</dt><dd>Theo cấu hình của An Phát</dd>
            <dt class="text-slate-500">Sold-To Party</dt><dd class="font-mono">${o.customer_id || "-"}</dd>
            <dt class="text-slate-500">Ship-To Party (WE)</dt><dd>${esc(o.ship_address)}</dd>
            <dt class="text-slate-500">Req. Deliv. Date</dt><dd>${vnDate(o.requested_delivery_date)}</dd>
            <dt class="text-slate-500">Cust. Reference</dt><dd class="font-mono">${o.email_id}</dd>
            <dt class="text-slate-500">Document Date</dt><dd>${e.received_at.slice(0, 10)}</dd></dl>
          <table class="w-full text-xs"><thead class="text-left text-slate-500"><tr><th class="px-2">Item</th><th class="px-2">Material</th><th class="px-2 text-right">Order Qty</th><th class="px-2">Sales Unit</th></tr></thead><tbody>${sap}</tbody></table>
          <div class="text-xs text-slate-500 mt-2">Đơn giá do SAP tự xác định (điều kiện PR00). Sales Order chỉ được tạo sau khi Sales Admin xác nhận.</div>`, "", "doc")}
      </div>
      <div class="col-span-7 space-y-4">
        ${card("Đơn nháp", `
          <div class="grid grid-cols-2 gap-3 mb-4">
            <div><div class="text-xs text-slate-500 mb-1">Khách hàng (tra theo địa chỉ người gửi)</div>
              <div class="border border-slate-200 rounded-lg px-2.5 py-1.5 bg-slate-50"><b>${esc(c.name || "-")}</b> <span class="text-slate-500">${o.customer_id || ""}</span></div></div>
            <div class="${o.date_needs_review ? "review rounded-lg" : ""} p-1"><div class="text-xs text-slate-500 mb-1">Ngày giao yêu cầu ${o.date_needs_review ? "· email không nêu, mặc định ngày làm việc kế tiếp" : ""}</div>
              <input id="ddate" ${ro ? "disabled" : ""} value="${vnDate(o.requested_delivery_date)}" class="border border-slate-300 rounded-lg px-2.5 py-1.5 w-full bg-white"></div>
            <div class="col-span-2 ${o.address_needs_review ? "review rounded-lg" : ""} p-1"><div class="text-xs text-slate-500 mb-1">Địa chỉ giao ${o.address_needs_review ? "· email không nêu, dùng địa chỉ mặc định" : ""}</div>
              <select id="daddr" ${ro ? "disabled" : ""} class="border border-slate-300 rounded-lg px-2.5 py-1.5 w-full bg-white">${addrs.map((a) => `<option ${a === o.ship_address ? "selected" : ""}>${esc(a)}</option>`).join("")}</select></div>
            ${o.customer_note ? `<div class="col-span-2 text-xs"><span class="text-slate-500">Ghi chú:</span> ${esc(o.customer_note)}</div>` : ""}
          </div>
          <table class="w-full text-sm"><thead class="text-left text-xs text-slate-500 uppercase tracking-wide"><tr>
            <th class="pb-2 px-2">#</th><th class="px-2">Tên gọi trong email</th><th class="px-2 text-right">SL</th><th class="px-2">ĐV</th>
            <th class="px-2">Mã hàng (SKU)</th><th class="px-2 text-right">SL theo ĐV bán</th><th class="px-2 text-center">Điểm</th><th class="px-2">Cần kiểm tra</th></tr></thead>
            <tbody>${itemRows}</tbody></table>
          <div id="aliasAsk"></div>
          ${isAdmin() && !decided ? `<div class="mt-5 pt-4 border-t border-slate-100 flex items-center gap-2 flex-wrap">
            <button id="bConfirm" ${block.length ? "disabled" : ""} class="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg font-medium shadow-sm ${block.length ? "bg-slate-100 text-slate-400 cursor-not-allowed" : "bg-emerald-600 text-white hover:bg-emerald-700"}">${ico("check")}Xác nhận</button>
            <button id="bAsk" class="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg border border-violet-300 text-violet-700 hover:bg-violet-50 font-medium">${ico("mail")}Đề nghị bổ sung</button>
            <button id="bReject" class="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg border border-rose-300 text-rose-700 hover:bg-rose-50 font-medium">${ico("x")}Từ chối</button>
            ${block.length ? `<span class="inline-flex items-center gap-1.5 text-xs text-rose-700 ml-2">${ico("alert")}Chưa xác nhận được: ${block.map(esc).join("; ")}</span>` : ""}</div>` : ""}
          ${decided ? `<div class="mt-5 pt-4 border-t border-slate-100 text-sm flex items-center gap-2 ${o.status === "confirmed" ? "text-emerald-700" : "text-rose-700"}">${ico(o.status === "confirmed" ? "check" : "x")}${o.status === "confirmed" ? "Đã xác nhận. Yêu cầu tạo Sales Order đã gửi SAP; email xác nhận gửi khách sau khi SAP trả số đơn." : `Đã từ chối. Lý do: ${esc(o.reject_reason)}`}</div>` : ""}
          ${o.status === "waiting_customer" ? `<div class="mt-3 text-sm text-violet-700 flex items-center gap-2">${ico("mail")}Đã gửi email đề nghị bổ sung. Phản hồi của khách sẽ được cập nhật vào đơn này.</div>` : ""}`, "", "doc")}
        ${card("Nhật ký thay đổi", logs.length ? `<table class="w-full text-xs"><thead class="text-left text-slate-500"><tr><th class="px-2 pb-1">Dòng</th><th class="px-2">Trường</th><th class="px-2">Giá trị cũ</th><th class="px-2">Giá trị mới</th><th class="px-2">Do</th></tr></thead><tbody>
          ${logs.map((l) => `<tr class="border-t border-slate-100"><td class="px-2 py-1">${l.line_no ?? ""}</td><td class="px-2">${l.field_name}</td><td class="px-2">${esc(l.old_value ?? "")}</td><td class="px-2">${esc(l.new_value ?? "")}</td>
            <td class="px-2">${l.edited_by ? userName(l.edited_by) : `Email sửa đơn ${l.source_email_id}`}</td></tr>`).join("")}</tbody></table>` : '<div class="text-slate-400 text-xs">Chưa có thay đổi nào.</div>', "", "history")}
      </div>
    </div>`;

  document.querySelectorAll("select.sku").forEach((s) => (s.onchange = (ev) => {
    const it = o.items[+s.dataset.i];
    let v = ev.target.value;
    if (v === "__other") { v = prompt("Nhập mã SKU (ví dụ VO004):", "") || ""; v = v.trim().toUpperCase(); if (!D.products[v]) { mh02(emailId); return; } }
    if (!v || v === it.sku) return;
    addLog(o, "sku", it.sku, v, it.line_no);
    it.sku = v; it.match_status = "manual"; it.suggestions = [];
    const nb = toBase(v, it.qty_raw, it.unit_raw);
    if (nb !== it.qty_base) { addLog(o, "qty_base", it.qty_base, nb, it.line_no); it.qty_base = nb; }
    o.status = blockers(o).length || o.items.some((x) => itemFlags(x).length) ? "needs_review" : "draft";
    const exists = D.aliases.some((a) => a.status === "active" && (a.customer_id === o.customer_id || !a.customer_id) && a.alias_text.toLowerCase() === it.product_text.toLowerCase());
    mh02(emailId);
    if (!exists) $("#aliasAsk").innerHTML = `<div class="mt-4 px-4 py-3 rounded-xl bg-sky-50 border border-sky-200 text-sm flex items-center gap-3">
      Lưu “${esc(it.product_text)}” làm bí danh của ${o.customer_id} cho mã ${v}? Lần sau hệ thống sẽ tự nhận ra tên gọi này.
      <button id="aYes" class="ml-auto px-3 py-1.5 rounded-lg bg-sky-700 text-white font-medium whitespace-nowrap">Lưu bí danh</button><button id="aNo" class="px-3 py-1.5 rounded-lg border border-slate-300 bg-white whitespace-nowrap">Không lưu</button></div>`;
    const y = $("#aYes"); if (y) { y.onclick = () => { D.aliases.push({ alias_id: "AL" + String(D.aliases.length + 1).padStart(3, "0"), customer_id: o.customer_id, alias_text: it.product_text, sku: v, status: "active", created_by: state.user.username }); $("#aliasAsk").innerHTML = ""; toast("Đã lưu bí danh. Xem trong Danh mục SKU."); }; $("#aNo").onclick = () => ($("#aliasAsk").innerHTML = ""); }
  }));
  document.querySelectorAll("input.qb").forEach((inp) => (inp.onchange = () => {
    const it = o.items[+inp.dataset.i], v = inp.value === "" ? null : Number(inp.value);
    if (v === it.qty_base) return;
    addLog(o, "qty_base", it.qty_base, v, it.line_no); it.qty_base = v; if (it.qty_raw === null && v !== null) it.qty_raw = v;
    o.status = blockers(o).length || o.items.some((x) => itemFlags(x).length) ? "needs_review" : "draft"; mh02(emailId);
  }));
  const dd = $("#ddate"); if (dd && !ro) dd.onchange = () => { const m = dd.value.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})/); if (!m) { mh02(emailId); return; }
    const v = `${m[3]}-${m[2].padStart(2, "0")}-${m[1].padStart(2, "0")}`; addLog(o, "requested_delivery_date", o.requested_delivery_date, v); o.requested_delivery_date = v; o.date_needs_review = false; mh02(emailId); };
  const da = $("#daddr"); if (da && !ro) da.onchange = () => { addLog(o, "ship_address", o.ship_address, da.value); o.ship_address = da.value; o.address_needs_review = false; mh02(emailId); };
  const decide = (st, reason) => {
    o.status = st; o.decided_by = state.user.username; o.reject_reason = reason || null;
    if (o._opened) { state.timing.push({ email_id: o.email_id, decision: ORDER_ST[st], user: state.user.full_name, seconds: Math.round((Date.now() - o._opened) / 1000), edits: D.logs.filter((l) => l.order_id === o.order_id && l.edited_by).length }); saveTiming(); }
    o.locked_by = null; mh02(emailId);
  };
  const bc = $("#bConfirm"); if (bc) bc.onclick = () => { if (!blockers(o).length) { decide("confirmed"); toast(`Đã xác nhận đơn ${o.email_id} và gửi yêu cầu tạo Sales Order.`); } };
  const ba = $("#bAsk"); if (ba) ba.onclick = () => { o.status = "waiting_customer"; o.locked_by = null; mh02(emailId); toast("Đã gửi email đề nghị khách bổ sung."); };
  const br = $("#bReject"); if (br) br.onclick = () => {
    $("#modal").classList.remove("hidden");
    $("#modal").innerHTML = `<div class="bg-white rounded-2xl shadow-xl p-6 w-[480px]"><div class="flex items-center gap-3 mb-3"><span class="w-10 h-10 rounded-full bg-rose-50 text-rose-600 flex items-center justify-center">${ico("x", "w-5 h-5")}</span>
      <div><div class="font-semibold text-slate-900">Từ chối đơn ${o.email_id}</div><div class="text-xs text-slate-500">Lý do sẽ được lưu vào nhật ký của đơn.</div></div></div>
      <textarea id="rr" rows="3" class="w-full ${inputCls}" placeholder="Lý do từ chối (bắt buộc)"></textarea>
      <div id="rerr" class="text-rose-700 text-xs h-4 mt-1"></div>
      <div class="flex justify-end gap-2 mt-2"><button id="rc" class="px-4 py-2 rounded-lg border border-slate-300">Hủy</button><button id="ro" class="px-4 py-2 rounded-lg bg-rose-600 text-white font-medium">Từ chối đơn</button></div></div>`;
    $("#rc").onclick = () => $("#modal").classList.add("hidden");
    $("#ro").onclick = () => { const r = $("#rr").value.trim(); if (!r) { $("#rerr").textContent = "Phải nhập lý do từ chối."; return; } $("#modal").classList.add("hidden"); decide("rejected", r); toast(`Đã từ chối đơn ${o.email_id}.`); };
  };
}

/* ---------- Danh mục SKU và bí danh ---------- */
function mh03(q = "", cust = "") {
  nav("danh-muc");
  const nq = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/đ/g, "d").toLowerCase();
  const prods = Object.values(D.products).filter((p) => !q || nq(p.sku + " " + p.name).includes(nq(q)));
  const al = D.aliases.filter((a) => (!cust || a.customer_id === cust || (cust === "_" && !a.customer_id)) && (!q || nq(a.alias_text + " " + a.sku).includes(nq(q))));
  const canAdd = isAdmin() || state.user.role === "system_admin", canStop = state.user.role === "system_admin";
  $("#app").innerHTML = `
    ${pageHead("Danh mục SKU và bí danh", `${Object.keys(D.products).length} SKU đồng bộ từ SAP · ${D.aliases.filter((a) => a.status === "active").length} bí danh đang dùng`,
      `<div class="relative"><span class="absolute left-2.5 top-2 text-slate-400">${ico("search")}</span><input id="q" value="${esc(q)}" placeholder="Tìm mã, tên hàng hoặc tên gọi…" class="${inputCls} pl-8 w-80"></div>`)}
    <div class="grid grid-cols-12 gap-4">
      <div class="col-span-7">${card(`SKU <span class="font-normal text-slate-500">(${prods.length})</span>`, `<div class="max-h-[760px] overflow-auto"><table class="w-full text-sm">
        <thead class="text-left text-xs text-slate-500 uppercase tracking-wide sticky top-0 bg-white"><tr><th class="pb-2 px-2">SKU</th><th class="px-2">Tên hàng</th><th class="px-2">ĐV bán</th><th class="px-2">Quy cách</th><th class="px-2 text-right">Ngưỡng bất thường</th><th class="px-2 text-center">Bí danh</th></tr></thead><tbody>
        ${prods.map((p) => `<tr class="border-t border-slate-100"><td class="py-1.5 px-2 font-mono text-xs">${p.sku}</td><td class="px-2">${esc(p.name)}</td><td class="px-2">${p.unit}</td>
          <td class="px-2 text-slate-600">${p.pack_unit ? `1 ${p.pack_unit} = ${p.pack_size} ${p.unit}` : "bán lẻ"}</td><td class="px-2 text-right tabnum">${p.max_normal_qty}</td>
          <td class="px-2 text-center tabnum">${D.aliases.filter((a) => a.sku === p.sku && a.status === "active").length || ""}</td></tr>`).join("")}</tbody></table></div>`, "", "box")}</div>
      <div class="col-span-5 space-y-4">
        ${card(`Bí danh <select id="ac" class="ml-auto ${inputCls} text-xs font-normal"><option value="">Mọi khách</option><option value="_" ${cust === "_" ? "selected" : ""}>Bí danh chung</option>
          ${Object.keys(D.customers).map((k) => `<option value="${k}" ${k === cust ? "selected" : ""}>${k} · ${esc(D.customers[k].name)}</option>`).join("")}</select>`,
          `<div class="max-h-[430px] overflow-auto"><table class="w-full text-sm"><thead class="text-left text-xs text-slate-500 uppercase tracking-wide"><tr><th class="pb-2 px-2">Mã</th><th class="px-2">Khách</th><th class="px-2">Tên gọi</th><th class="px-2">SKU</th><th class="px-2"></th></tr></thead><tbody>
          ${al.map((a) => `<tr class="border-t border-slate-100 ${a.status === "inactive" ? "text-slate-400 line-through" : ""} ${a.created_by ? "bg-sky-50" : ""}"><td class="py-1.5 px-2 font-mono text-xs">${a.alias_id}</td><td class="px-2 text-xs">${a.customer_id || "chung"}</td>
            <td class="px-2">${esc(a.alias_text)}</td><td class="px-2 font-mono text-xs">${a.sku}</td>
            <td class="px-2 text-right">${canStop && a.status === "active" ? `<button data-id="${a.alias_id}" class="stop text-xs text-rose-700 hover:underline">Ngừng dùng</button>` : ""}</td></tr>`).join("")}</tbody></table></div>`)}
        ${canAdd ? card("Thêm bí danh", `<div class="grid grid-cols-2 gap-2">
          <select id="nc" class="${inputCls} col-span-2"><option value="">Bí danh chung (mọi khách)</option>${Object.keys(D.customers).map((k) => `<option value="${k}" ${k === cust ? "selected" : ""}>${k} · ${esc(D.customers[k].name)}</option>`).join("")}</select>
          <input id="nt" placeholder="Tên gọi của khách" class="${inputCls}"><input id="ns" placeholder="Mã SKU" class="${inputCls} font-mono">
          <button id="nadd" class="col-span-2 px-3 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-medium">Lưu bí danh</button><div id="nmsg" class="col-span-2 text-xs"></div></div>`) :
          card("", `<div class="text-slate-500 text-sm flex items-center gap-2">${ico("lock", "w-5 h-5 text-slate-400")}Trưởng phòng kinh doanh chỉ xem danh mục; thêm, sửa bí danh do Sales Admin và Quản trị hệ thống thực hiện.</div>`)}
      </div></div>`;
  $("#q").onchange = (e) => mh03(e.target.value, cust);
  $("#ac").onchange = (e) => mh03(q, e.target.value);
  document.querySelectorAll(".stop").forEach((b) => (b.onclick = () => { D.aliases.find((a) => a.alias_id === b.dataset.id).status = "inactive"; mh03(q, cust); toast(`Đã ngừng dùng bí danh ${b.dataset.id}.`); }));
  const add = $("#nadd"); if (add) add.onclick = () => {
    const c = $("#nc").value || null, t = $("#nt").value.trim(), s = $("#ns").value.trim().toUpperCase();
    if (!t || !D.products[s]) { $("#nmsg").innerHTML = '<span class="text-rose-700">Cần tên gọi và mã SKU có trong danh mục.</span>'; return; }
    const dup = D.aliases.find((a) => a.status === "active" && (a.customer_id || null) === c && a.alias_text.toLowerCase() === t.toLowerCase());
    if (dup && dup.sku !== s) {
      $("#nmsg").innerHTML = `<span class="text-rose-700">Tên gọi này đã trỏ tới ${dup.sku} (${dup.alias_id}). Một tên gọi chỉ trỏ tới một SKU.</span> <button id="rep" class="underline">Ngừng ${dup.alias_id} và lưu mới</button>`;
      $("#rep").onclick = () => { dup.status = "inactive"; D.aliases.push({ alias_id: "AL" + String(D.aliases.length + 1).padStart(3, "0"), customer_id: c, alias_text: t, sku: s, status: "active", created_by: state.user.username }); mh03(q, cust); toast("Đã thay bí danh cũ bằng bí danh mới."); };
      return;
    }
    if (dup) { $("#nmsg").innerHTML = '<span class="text-slate-600">Bí danh này đã có.</span>'; return; }
    D.aliases.push({ alias_id: "AL" + String(D.aliases.length + 1).padStart(3, "0"), customer_id: c, alias_text: t, sku: s, status: "active", created_by: state.user.username });
    mh03(q, cust); toast("Đã lưu bí danh mới.");
  };
}

/* ---------- Dashboard KPI ---------- */
function bar(v, max, cls) { return `<div class="h-2.5 rounded-full bar-grow ${cls}" style="width:${max ? (100 * v / max).toFixed(1) : 0}%"></div>`; }
function mh04() {
  nav("bao-cao");
  const S = D.stats, ev = S.eval;
  const pct = (a, b) => (b ? (100 * a / b).toLocaleString("vi-VN", { maximumFractionDigits: 1 }) : "0") + "%";
  const days = Object.entries(S.by_day).sort();
  const maxE = Math.max(...days.map(([, v]) => v.emails));
  const st = Object.keys(ORDER_ST).map((k) => [k, D.orders.filter((o) => o.status === k).length]);
  const t = state.timing, avg = t.length ? t.reduce((s, x) => s + x.seconds, 0) / t.length : null;
  const kpi = (icon, name, now, target, value, note, ok) => `<div class="kpi bg-white rounded-xl border border-slate-200 shadow-sm p-5">
      <div class="flex items-center gap-2 text-sm font-medium text-slate-600"><span class="w-7 h-7 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">${ico(icon)}</span>${name}</div>
      <div class="${/^[\d,.]+ ?(%|phút)$/.test(value) ? "text-3xl" : "text-xl py-1"} font-semibold mt-3 tabnum ${ok === true ? "text-emerald-600" : ok === false ? "text-rose-600" : "text-slate-400"}">${value}</div>
      <div class="flex gap-2 mt-2 text-xs"><span class="px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">Hiện trạng ${now}</span><span class="px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700">Mục tiêu ${target}</span></div>
      <div class="text-xs text-slate-500 mt-2 leading-relaxed">${note}</div></div>`;
  $("#app").innerHTML = `
    ${pageHead("Dashboard KPI", `Tuần 02-07/11/2026 · ${S.emails} email · ${S.orders} đơn nháp`)}
    <div class="grid grid-cols-4 gap-4 mb-5">
      ${kpi("clock", "Thời gian xử lý mỗi đơn", "6 phút", "≤ 1,5 phút", avg === null ? "Chưa có lượt duyệt" : (avg / 60).toLocaleString("vi-VN", { maximumFractionDigits: 2 }) + " phút", avg === null ? "Đo từ lúc mở đơn đến lúc xác nhận hoặc từ chối; hãy duyệt một đơn để có số liệu" : `Trung bình ${t.length} lượt duyệt`, avg === null ? null : avg <= 90)}
      ${kpi("doc", "Tỷ lệ đơn nháp phải sửa", "Chưa có", "< 20%", pct(ev.don_cham - ev.don_dat_ngay, ev.don_cham), `Ước tính: ${ev.don_cham - ev.don_dat_ngay}/${ev.don_cham} đơn của tập kiểm tra chưa đạt ngay`, ev.kpi02_uoc_tinh < 0.2)}
      ${kpi("alert", "Đơn sai lọt qua sau duyệt", "4%", "< 1%", "Đo trong pilot", "Cần dữ liệu đơn điều chỉnh do sai mã hàng hoặc sai số lượng", null)}
      ${kpi("check", "Đơn trước 17h00 xác nhận trong ngày", "80%", "≥ 95%", "Đo trong pilot", "Cần thời điểm xác nhận thật của Sales Admin", null)}
    </div>
    <div class="grid grid-cols-12 gap-4">
      <div class="col-span-7 space-y-4">
        ${card("Email và đơn nháp theo ngày nhận", `<table class="w-full text-sm">${days.map(([d, v]) => `<tr><td class="py-1.5 w-32 whitespace-nowrap pr-3 text-slate-600">${dayName(d)} ${fmtDate(d)}</td>
          <td class="w-full"><div class="flex flex-col gap-1">${bar(v.emails, maxE, "bg-slate-300")}${bar(v.orders, maxE, "bg-indigo-500")}</div></td>
          <td class="pl-3 text-xs tabnum whitespace-nowrap">${v.emails} email · ${v.orders} đơn mới · ${v.after_cutoff} sau 17h00</td></tr>`).join("")}</table>
          <div class="text-xs text-slate-500 mt-2"><span class="inline-block w-3 h-2 rounded-full bg-slate-300 mr-1"></span>Email nhận <span class="inline-block w-3 h-2 rounded-full bg-indigo-500 ml-3 mr-1"></span>Email tạo đơn nháp mới</div>`, "", "mail")}
        ${card("Độ chính xác của AI trên 30 email kiểm tra", `<table class="w-full text-sm"><tbody>
          <tr><td class="py-1">Phân loại email đúng</td><td class="text-right tabnum">${ev.phan_loai_dung}/${ev.so_email}</td><td class="text-right tabnum w-20">${pct(ev.phan_loai_dung, ev.so_email)}</td></tr>
          ${Object.entries(ev.truong).map(([k, v]) => `<tr class="border-t border-slate-100"><td class="py-1">Trích xuất đúng: ${k}</td><td class="text-right tabnum">${v.dung}/${v.tong}</td><td class="text-right tabnum">${pct(v.dung, v.tong)}</td></tr>`).join("")}
          <tr class="border-t border-slate-100"><td class="py-1">Mã hàng đúng ở vị trí số 1 (top-1)</td><td class="text-right tabnum">${ev.sku_top1}/${ev.sku_dong}</td><td class="text-right tabnum">${pct(ev.sku_top1, ev.sku_dong)}</td></tr>
          <tr class="border-t border-slate-100"><td class="py-1">Mã hàng đúng nằm trong 3 gợi ý (top-3)</td><td class="text-right tabnum">${ev.sku_top3}/${ev.sku_dong}</td><td class="text-right tabnum">${pct(ev.sku_top3, ev.sku_dong)}</td></tr>
          <tr class="border-t border-slate-100 font-medium"><td class="py-1">Đơn nháp đạt ngay, không phải sửa</td><td class="text-right tabnum">${ev.don_dat_ngay}/${ev.don_cham}</td><td class="text-right tabnum">${pct(ev.don_dat_ngay, ev.don_cham)}</td></tr></tbody></table>`, "", "chart")}
      </div>
      <div class="col-span-5 space-y-4">
        ${card("Trạng thái đơn hiện tại", st.map(([k, n]) => `<div class="flex items-center gap-2 py-1.5"><span class="w-40">${badge(k)}</span><div class="flex-1 bg-slate-100 rounded-full">${bar(n, S.orders, ORDER_DOT[k])}</div><span class="tabnum w-8 text-right font-medium">${n}</span></div>`).join(""), "", "doc")}
        ${card("Đối chiếu mã hàng của tất cả dòng hàng", [["Khớp (≥ 90 điểm)", S.matched, "bg-emerald-500"], ["Gợi ý 3 mã (75-89 hoặc hòa điểm)", S.suggested, "bg-amber-400"], ["Không khớp (< 75)", S.unmatched, "bg-rose-400"]]
          .map(([l, n, c]) => `<div class="flex items-center gap-2 py-1.5"><span class="w-56 text-xs">${l}</span><div class="flex-1 bg-slate-100 rounded-full">${bar(n, S.lines, c)}</div><span class="tabnum w-20 text-right text-xs">${n} · ${pct(n, S.lines)}</span></div>`).join("") + `<div class="text-xs text-slate-500 mt-1">${S.lines} dòng hàng khi đơn nháp được tạo</div>`, "", "search")}
        ${card(`Thời gian duyệt đơn <span class="font-normal text-slate-400">${t.length} lượt</span>`, t.length ? `<table class="w-full text-xs"><thead class="text-left text-slate-500"><tr><th class="pb-1">Mã email</th><th>Quyết định</th><th>Người duyệt</th><th class="text-right">Giây</th><th class="text-right">Số lần sửa</th></tr></thead><tbody>
          ${t.map((x) => `<tr class="border-t border-slate-100"><td class="py-1">${x.email_id}</td><td>${x.decision}</td><td>${esc(x.user)}</td><td class="text-right tabnum">${x.seconds}</td><td class="text-right tabnum">${x.edits}</td></tr>`).join("")}</tbody></table>
          <div class="flex gap-2 mt-3"><button id="csv" class="px-3 py-1.5 rounded-lg border border-slate-300 text-xs">Tải CSV</button><button id="tclr" class="px-3 py-1.5 rounded-lg border border-slate-300 text-xs">Xóa dữ liệu thời gian</button></div>`
          : '<div class="text-xs text-slate-500 leading-relaxed">Mở một đơn bằng tài khoản Sales Admin rồi xác nhận hoặc từ chối: thời gian từ lúc mở đến lúc quyết định được ghi lại ở đây.</div>', "", "clock")}
      </div></div>`;
  const csv = $("#csv"); if (csv) csv.onclick = () => {
    const rows = [["email_id", "quyet_dinh", "nguoi_duyet", "giay", "so_lan_sua"], ...t.map((x) => [x.email_id, x.decision, x.user, x.seconds, x.edits])];
    const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob(["﻿" + rows.map((r) => r.join(",")).join("\n")], { type: "text/csv" })); a.download = "I2O_ThoiGianDuyet.csv"; a.click();
  };
  const tc = $("#tclr"); if (tc) tc.onclick = () => { state.timing = []; saveTiming(); mh04(); };
}

function route() {
  $("#modal").classList.add("hidden");
  const [r, arg] = location.hash.slice(1).split("/");
  if (r === "don" || r === "mh02") mh02(arg); else if (r === "danh-muc" || r === "mh03") mh03(); else if (r === "bao-cao" || r === "mh04") mh04(); else mh01();
  window.scrollTo(0, 0);
}
window.addEventListener("hashchange", route);
route();
