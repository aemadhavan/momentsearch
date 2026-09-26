/* Shared by every MomentSearch page: identity, API calls, markdown, moment
 * cards and the player modal. No build step — plain <script> before the page's
 * own script.
 */
const $=s=>document.querySelector(s);
const $$=s=>Array.from(document.querySelectorAll(s));
const esc=s=>String(s==null?"":s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const REDUCED = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/* ---------- identity ----------
   There is one account and you are always it. No sign-in, no sign-up, no token,
   nothing in localStorage: the server pins every request to its single tenant
   (config.SINGLE_USER_ID) and ignores any identity header a client sends, so
   there is nothing for the browser to prove or remember.

   USER_NAME is a label for the header, not a credential. If real auth ever
   comes back, this is the one block that has to learn about sessions again. */
const USER_NAME="admin";

/* ---------- top-nav affordance ----------
   The pages that need a way into the workspace carry one #navAuth link in the
   header, so their top-right is identical. The landing page deliberately has
   none — its hero button is the primary CTA and a second copy of it in the
   header only raises the question of how they differ. Call once after the
   header exists; harmless (a no-op) where there is no link. */
function wireNav(){
  const a=$("#navAuth"); if(!a) return;
  a.href="/app"; a.textContent="Workspace →"; a.title="Open the workspace";
}

/* Use this rather than fetch() for our own API: one place to add a header if
   this ever needs to carry credentials again. */
function api(path, opts={}){
  const headers=Object.assign({}, opts.headers||{});
  return fetch(path, Object.assign({}, opts, {headers}));
}
async function apiJSON(path, opts){
  const r=await api(path, opts);
  const d=await r.json().catch(()=>({}));
  if(!r.ok) throw new Error(d.detail || r.statusText || "Request failed");
  return d;
}

/* ---------- markdown (bold, code, bullets, [n] citation pills) ---------- */
function mdInline(t){
  t=esc(t).replace(/\*\*(.+?)\*\*/g,'<b>$1</b>').replace(/`([^`]+?)`/g,'<code class="px-1 rounded bg-paper2 text-[13px]">$1</code>');
  return t.replace(/\[(\d+(?:\s*,\s*\d+)*)\]/g,(_,g)=>g.split(/\s*,\s*/).map(n=>
    `<span class="cite" data-n="${n.trim()}" title="Play this moment">${n.trim()}</span>`).join(''));
}
/* Blocks: GFM tables (the "Who said what" table), ### headings, - bullets, and
   paragraphs. Tables are the reason this exists — without them the answer's
   `| Speaker | … |` rows render as literal-pipe paragraphs. */
function renderMarkdown(md){
  const lines=(md||"").split(/\n/); let html="",inUl=false,i=0;
  const closeUl=()=>{if(inUl){html+="</ul>";inUl=false;}};
  const isRow=s=>/^\|.*\|$/.test(s);
  const cells=s=>s.replace(/^\||\|$/g,"").split("|").map(c=>c.trim());
  const isSep=s=>isRow(s)&&cells(s).every(c=>/^:?-{2,}:?$/.test(c));
  const nextNonBlank=k=>{ while(k<lines.length && lines[k].trim()==="") k++; return k; };
  while(i<lines.length){
    const l=(lines[i]||"").trim();
    // GFM table: a header row whose next non-blank line is a `---` separator.
    // Blank lines between rows are tolerated (models often emit them).
    if(isRow(l)){
      const sep=nextNonBlank(i+1);
      if(sep<lines.length && isSep(lines[sep].trim())){
        closeUl();
        const head=cells(l); let body="",j=sep+1;
        while(j<lines.length){
          const jl=lines[j].trim();
          if(jl===""){ j++; continue; }
          if(!isRow(jl)) break;
          body+=`<tr>${cells(jl).map(c=>`<td class="px-3 py-2 border-t border-line align-top">${mdInline(c)}</td>`).join("")}</tr>`;
          j++;
        }
        html+=`<div class="overflow-x-auto my-4"><table class="w-full text-[13px] border border-line rounded-lg">`
          +`<thead><tr class="bg-paper2">${head.map(c=>`<th class="px-3 py-2 text-left font-600">${mdInline(c)}</th>`).join("")}</tr></thead>`
          +`<tbody>${body}</tbody></table></div>`;
        i=j; continue;
      }
    }
    // headings (### Who said what -> a modest subheading)
    const h=l.match(/^#{1,6}\s+(.*)$/);
    if(h){ closeUl(); html+=`<div class="display font-600 text-[15px] mt-5 mb-2">${mdInline(h[1])}</div>`; i++; continue; }
    // bullets
    if(/^[-*]\s+/.test(l)){ if(!inUl){html+="<ul>";inUl=true;} html+=`<li>${mdInline(l.replace(/^[-*]\s+/,''))}</li>`; i++; continue; }
    // paragraph
    closeUl(); if(l) html+=`<p class="mb-3">${mdInline(l)}</p>`; i++;
  }
  closeUl(); return html;
}

/* ---------- moment cards ---------- */
function ytIdOf(c){
  if(c.video_id && c.video_id.startsWith("yt_")) return c.video_id.slice(3);
  const m=(c.url||"").match(/(?:youtu\.be\/|v=)([\w-]{11})/); return m?m[1]:null;
}
function modTags(mods){
  return (mods||[]).map(m=>m==="frame"
    ? '<span class="text-[9px] px-1 rounded bg-coral/15 text-coral2">seen</span>'
    : '<span class="text-[9px] px-1 rounded bg-[#cfe8d6] text-[#1f7a43]">said</span>').join(" ");
}
/* Multi-part questions (server: MULTI_QUERY). The server splits "what does A say,
   and how does B respond?" into parts and searches each; every moment then says
   which part(s) found it (Q1/Q2), and the answer lists the parts it searched as.
   A single-part answer carries neither, so both render nothing. */
function partTags(parts){
  return (parts||[]).map(p=>
    `<span class="text-[9px] px-1 rounded border border-line text-muted" title="found for part ${p} of your question">Q${p}</span>`).join(" ");
}
function partsLine(parts){
  if(!parts || parts.length<2) return "";
  return `<div class="text-[11.5px] text-muted mt-3 leading-relaxed">
    <span class="text-[10px] uppercase tracking-wider font-semibold mr-1">Searched as</span>
    ${parts.map((p,i)=>`<span class="inline-block mr-2"><span class="text-[9px] px-1 rounded border border-line text-muted mr-1">Q${i+1}</span>${esc(p)}</span>`).join("")}
  </div>`;
}
/* Text-only moments have no frame; they're always YouTube, so fall back to the
   video's thumbnail rather than showing an empty box. */
function modalityBadge(c){
  const k = c.kind || (c.locator?.page ? "paper" : (c.locator?.slide ? "deck" : "video"));
  if(k === "paper"){
    const p = c.locator?.page || c.page || 1;
    return `<span class="text-[9px] px-1.5 py-0.5 rounded bg-blue-100 text-blue-800 font-bold tracking-wide">📄 Paper · p.${p}</span>`;
  }
  if(k === "deck"){
    const s = c.locator?.slide || c.slide || 1;
    return `<span class="text-[9px] px-1.5 py-0.5 rounded bg-purple-100 text-purple-800 font-bold tracking-wide">📊 Slide ${s}</span>`;
  }
  const ts = c.timestamp || (c.locator?.start_ms ? fmtT(c.locator.start_ms/1000) : "0:00");
  return `<span class="text-[9px] px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 font-bold tracking-wide">🎬 Video · ${ts}</span>`;
}

function thumbOf(c){
  const k = c.kind || (c.locator?.page ? "paper" : (c.locator?.slide ? "deck" : "video"));
  if(k === "paper" || k === "deck") return null;
  const yid=ytIdOf(c);
  return c.thumbnail || c.preview || (yid ? `https://img.youtube.com/vi/${yid}/hqdefault.jpg` : null);
}
/* A /api/videos row as something openMoment() can play: the video itself, from
   0:00, with no matched moment attached. */
function wholeVideo(v){
  return {n:0, whole:true, video_id:v.id, title:v.title||v.id, url:v.url||"",
          author:v.author||"", ms:0, timestamp:"0:00", deeplink:v.url||""};
}
/* "youtu.be/LPZh9BOjkQs" — a URL you can read at 12px. */
function shortUrl(url){
  return String(url||"").replace(/^https?:\/\//,"").replace(/^www\./,"").replace(/\/+$/,"");
}
function momentCard(c, i){
  const k = c.kind || (c.locator?.page ? "paper" : (c.locator?.slide ? "deck" : "video"));
  let thumb;
  if(k === "paper"){
    const p = c.locator?.page || c.page || 1;
    thumb = `<div class="w-full h-full flex flex-col items-center justify-center bg-blue-50 border-b border-blue-100 p-3 text-center">
      <div class="text-3xl mb-1">📄</div>
      <div class="text-[12px] font-bold text-blue-900">Academic Paper</div>
      <div class="text-[10px] text-blue-600 font-semibold">Page ${p}</div>
    </div>`;
  } else if(k === "deck"){
    const s = c.locator?.slide || c.slide || 1;
    thumb = `<div class="w-full h-full flex flex-col items-center justify-center bg-purple-50 border-b border-purple-100 p-3 text-center">
      <div class="text-3xl mb-1">📊</div>
      <div class="text-[12px] font-bold text-purple-900">Presentation Deck</div>
      <div class="text-[10px] text-purple-600 font-semibold">Slide ${s}</div>
    </div>`;
  } else {
    const img = thumbOf(c);
    thumb = img
      ? `<img loading="lazy" src="${esc(img)}" class="w-full h-full object-cover" onerror="this.style.opacity=0">`
      : `<div class="w-full h-full flex items-center justify-center text-muted text-xs p-2 text-center">transcript moment<br>(no frame)</div>`;
  }

  const quoteText = c.text || c.transcript || "";
  const quote = quoteText
    ? `<div class="text-[11px] text-muted italic mt-1 line-clamp-2">“${esc(quoteText)}”</div>` : "";
  const spk = c.speaker
    ? `<div class="text-[10px] font-600 text-coral2 mt-1 truncate">🎙 ${esc(c.speaker)}</div>` : "";

  const m = c.match;
  const relCls = m>=80 ? "text-[#1f7a43]" : m>=65 ? "text-[#8a6d1a]" : "text-muted";
  const rel = (m!=null)
    ? `<span class="text-[11px] font-600 ${relCls} ml-auto" title="match strength">${m}% match</span>`
    : (c.score ? `<span class="text-[11px] text-muted ml-auto">score ${c.score}</span>` : "");

  return `
  <button class="source pop text-left bg-card border border-line rounded-2xl overflow-hidden shadow-sm hover:border-coral transition" data-n="${c.n}" style="--i:${i||0}">
    <div class="aspect-video bg-paper2 overflow-hidden">${thumb}</div>
    <div class="p-3">
      <div class="flex items-center gap-2 mb-1 flex-wrap">
        <span class="text-[10px] font-bold text-white bg-coral rounded px-1.5 py-0.5">${c.n}</span>
        ${modalityBadge(c)}
        ${partTags(c.parts)}
        ${rel}
      </div>
      <div class="text-[12px] font-600 leading-snug line-clamp-2">${esc(c.title||c.sourceId||c.video_id)}</div>
      ${spk}
      ${quote}
    </div>
  </button>`;
}

/* ---------- player modal + synced transcript ----------
   openMoment(list, n) — click a card or a [n] pill; the moment opens seeked.
   YouTube plays through the IFrame Player API (so JS can seek AND read the
   current time — that's what moves the transcript); uploads through <video>.
   For papers and decks, renders document / slide viewer with direct jump link. */
let MODAL_LIST=[];
let YTP=null, VIDEOEL=null, SYNC=null, CUES=[], ACTIVELINE=-1, _ytApiP=null;

function ytApi(){                                   // load the IFrame API once
  if(window.YT && window.YT.Player) return Promise.resolve(window.YT);
  if(_ytApiP) return _ytApiP;
  _ytApiP=new Promise(res=>{
    const prev=window.onYouTubeIframeAPIReady;
    window.onYouTubeIframeAPIReady=()=>{ if(prev)prev(); res(window.YT); };
    const s=document.createElement("script"); s.src="https://www.youtube.com/iframe_api";
    document.head.appendChild(s);
  });
  return _ytApiP;
}
function fmtT(s){ s=Math.max(0,Math.floor(s||0)); return `${Math.floor(s/60)}:${String(s%60).padStart(2,"0")}`; }
function stopSync(){ if(SYNC){ clearInterval(SYNC); SYNC=null; } }
function teardownPlayer(){
  stopSync();
  try{ if(YTP&&YTP.destroy) YTP.destroy(); }catch(e){}
  YTP=null; VIDEOEL=null; CUES=[]; ACTIVELINE=-1;
  const box=$("#playerBox"); if(box) box.innerHTML="";
  const p=$("#transcriptPanel"); if(p) p.innerHTML="";
}
function seekTo(t){
  const s=Math.floor(t);
  if(YTP&&YTP.seekTo){ YTP.seekTo(s,true); if(YTP.playVideo) YTP.playVideo(); }
  else if(VIDEOEL){ try{ VIDEOEL.currentTime=s; if(VIDEOEL.play) VIDEOEL.play(); }catch(e){} }
}
function highlightAt(t){                            // move the transcript with time
  if(!CUES.length) return;
  let idx=-1;
  for(let i=0;i<CUES.length;i++){ if(t >= (CUES[i].t_start||0)-0.05) idx=i; else break; }
  if(idx===ACTIVELINE) return;
  ACTIVELINE=idx;
  const lines=$$("#transcriptPanel .tline");
  lines.forEach((el,i)=>el.classList.toggle("active", i===idx));
  if(idx>=0 && lines[idx]) lines[idx].scrollIntoView({block:"nearest", behavior:"smooth"});
}
async function loadTranscript(c, secs){             // GCP-only; no transcript -> hide panel
  const panel=$("#transcriptPanel"), wrap=$("#transcriptWrap");
  if(!panel || !wrap) return;
  CUES=[]; ACTIVELINE=-1;
  panel.innerHTML=`<div class="p-3 text-xs text-muted">Loading transcript…</div>`;
  try{
    const r=await api(`/api/transcript/${encodeURIComponent(c.video_id)}`);
    if(!r.ok) throw new Error("no transcript");
    CUES=(await r.json()).chunks||[];
  }catch(e){ CUES=[]; }
  if(!CUES.length){ wrap.classList.add("hidden"); return; }
  wrap.classList.remove("hidden");
  panel.innerHTML=CUES.map(cu=>
    `<button class="tline" data-t="${cu.t_start||0}"><span class="ts">${fmtT(cu.t_start)}</span>${esc(cu.text||"")}</button>`
  ).join("");
  $$("#transcriptPanel .tline").forEach(el=>el.onclick=()=>seekTo(+el.dataset.t));
  highlightAt(secs);
}

function openMoment(list, n){
  MODAL_LIST=list||[];
  const c=MODAL_LIST.find(x=>x.n===n); if(!c) return;
  const k = c.kind || (c.locator?.page ? "paper" : (c.locator?.slide ? "deck" : "video"));

  if(k === "paper" || k === "deck"){
    const isPaper = k === "paper";
    const locText = isPaper ? `Page ${c.locator?.page || c.page || 1}` : `Slide ${c.locator?.slide || c.slide || 1}`;
    $("#mTitle").textContent = c.title || c.sourceId || (isPaper ? "Academic Paper" : "Presentation Deck");
    $("#mMeta").textContent = `${isPaper ? "Research Paper" : "Presentation Deck"} · ${locText}`;
    $("#mFrame").style.display = "none";
    $("#mFrameLabel").textContent = `Verified Grounded Passage (${locText})`;
    $("#mFrameDesc").textContent = "Retrieved from shared Qdrant index with verified source locator.";
    $("#mOut").href = c.url || c.uri || "#";

    teardownPlayer();
    $("#modal").classList.remove("hidden");
    document.body.style.overflow="hidden";

    const box = $("#playerBox");
    const icon = isPaper ? "📄" : "📊";
    const badgeColor = isPaper ? "bg-blue-100 text-blue-900 border-blue-200" : "bg-purple-100 text-purple-900 border-purple-200";
    const btnColor = isPaper ? "bg-blue-600 hover:bg-blue-700" : "bg-purple-600 hover:bg-purple-700";
    const targetUrl = c.url || c.uri;

    box.innerHTML = `
      <div class="w-full h-full flex flex-col justify-center items-center p-6 bg-paper2 rounded-xl text-center overflow-y-auto">
        <div class="text-5xl mb-2">${icon}</div>
        <div class="text-base font-bold text-ink mb-1">${esc(c.title || c.sourceId)}</div>
        <div class="inline-block px-2.5 py-1 rounded-full text-xs font-semibold border ${badgeColor} mb-4">${locText}</div>
        <div class="max-w-lg w-full text-left bg-card p-4 rounded-xl border border-line text-sm text-ink mb-4 shadow-sm leading-relaxed whitespace-pre-wrap max-h-48 overflow-y-auto">“${esc(c.text || c.transcript || "")}”</div>
        ${targetUrl ? `<a href="${esc(targetUrl)}${isPaper ? '#page=' + (c.locator?.page || c.page || 1) : ''}" target="_blank" rel="noopener noreferrer" class="px-4 py-2 ${btnColor} text-white font-medium text-xs rounded-lg transition inline-flex items-center gap-1.5 shadow">Open Source Document ↗</a>` : ''}
      </div>
    `;
    const wrap = $("#transcriptWrap");
    if(wrap) wrap.classList.add("hidden");
    return;
  }

  const secs=Math.floor((c.ms||(c.locator?.start_ms ? c.locator.start_ms : 0))/1000);
  $("#mTitle").textContent=c.title||c.video_id;
  $("#mMeta").textContent = c.whole
    ? (c.author ? `By ${c.author} · playing from the start` : "Playing from the start")
    : c.transcript ? `“${c.transcript}”` : `Moment at ${c.timestamp}`;
  const preview=thumbOf(c);
  $("#mFrame").style.display = preview ? "" : "none";
  if(preview) $("#mFrame").src=preview;
  const isFrame=!!c.thumbnail;
  $("#mFrameLabel").textContent = c.whole ? "The whole video"
    : isFrame ? "Matched frame" : "Matched on transcript";
  $("#mFrameDesc").textContent = c.whole
    ? "Nothing was searched for yet. This is the source, playing from 0:00. The transcript beside it is click-to-jump."
    : isFrame
    ? "This is what CLIP matched your question against: the still it judged closest to what you asked."
    : "This moment matched on what was said (transcript). The still is the video at that moment. Press play to jump to the exact spot.";
  $("#mOut").href=c.deeplink||"#";

  teardownPlayer();
  $("#modal").classList.remove("hidden");
  document.body.style.overflow="hidden";
  const box=$("#playerBox"), yid=ytIdOf(c);
  if(yid){
    box.innerHTML=`<div id="ytplayer" class="w-full h-full"></div>`;
    ytApi().then(YT=>{
      YTP=new YT.Player("ytplayer",{
        videoId:yid,
        playerVars:{start:secs, autoplay:1, rel:0, modestbranding:1, playsinline:1},
        events:{ onReady:e=>{
          try{ e.target.seekTo(secs,true); e.target.playVideo(); }catch(_){}
          stopSync(); SYNC=setInterval(()=>{ try{ highlightAt(YTP.getCurrentTime()); }catch(_){} }, 500);
        } }
      });
    });
  } else {
    box.innerHTML=`<video class="w-full h-full" controls autoplay playsinline src="${esc(c.media_url||('/api/video/'+c.video_id))}"></video>`;
    VIDEOEL=box.querySelector("video");
    const seek=()=>{ try{VIDEOEL.currentTime=secs;}catch(e){} };
    if(VIDEOEL.readyState>=1) seek(); else VIDEOEL.addEventListener("loadedmetadata",seek,{once:true});
    VIDEOEL.addEventListener("timeupdate",()=>highlightAt(VIDEOEL.currentTime));
  }
  loadTranscript(c, secs);
}
function closeModal(){
  teardownPlayer();
  const m=$("#modal"); if(m) m.classList.add("hidden");
  document.body.style.overflow="";
}
function wireModal(){
  if(!$("#modal")) return;
  $("#mClose").onclick=closeModal;
  $("#modal").onclick=e=>{ if(e.target.id==="modal") closeModal(); };
  document.addEventListener("keydown",e=>{ if(e.key==="Escape") closeModal(); });
}

/* ---------- video status ---------- */
const INFLIGHT=["pending","queued","fetching","sampling","embedding"];
/* How long ingest took: added (created_at) -> ready (updated_at). Nothing
   touches the row after it's indexed, so updated_at is the finish time. */
function ingestDur(v){
  if(!v.created_at || !v.updated_at) return "";
  const s = Math.round((new Date(v.updated_at) - new Date(v.created_at))/1000);
  if(!(s > 0) || s > 86400) return "";           // guard clock skew / re-index
  return s < 60 ? `${s}s` : `${Math.floor(s/60)}m ${s%60}s`;
}
function statusBadge(v){
  const src = v.is_sample ? "sample" : (v.source==="youtube" ? "YouTube" : "upload");
  const pct = v.progress ? ` ${Math.round(v.progress*100)}%` : "";
  switch(v.status){
    case "indexed": {
      const t = ingestDur(v);
      return {icon:"✓", label:`${v.frame_count||0} frames · ${src}${t?` · indexed in ${t}`:""}`, c:"text-[#1f7a43]"};
    }
    case "pending":   return {icon:"◷", label:"waiting (fair queue)", c:"text-[#8a6d1a]"};
    case "queued":    return {icon:"◷", label:"queued",              c:"text-[#8a6d1a]"};
    case "fetching":  return {icon:"⏬", label:"fetching video…",     c:"text-[#8a6d1a]"};
    case "sampling":  return {icon:"⏳", label:"sampling"+pct,        c:"text-[#8a6d1a]"};
    case "embedding": return {icon:"⏳", label:"embedding"+pct,       c:"text-[#8a6d1a]"};
    case "failed":    return {icon:"⚠", label:"failed",              c:"text-coral2"};
    case "skipped":   return {icon:"↗", label:"already indexed",     c:"text-muted"};
    default:          return {icon:"•", label:v.status,              c:"text-muted"};
  }
}

/* SHA-256 of a file as lowercase hex — matches the server's content hash, so an
   identical re-upload can be detected BEFORE any bytes are sent (the instant
   reuse path). Needs a secure context (https / localhost); returns null if the
   Web Crypto API isn't available so the caller just falls back to a normal
   upload + server-side dedup. */
async function sha256Hex(file){
  try{
    if(!(crypto && crypto.subtle)) return null;
    const buf=await file.arrayBuffer();
    const d=await crypto.subtle.digest("SHA-256", buf);
    return [...new Uint8Array(d)].map(b=>b.toString(16).padStart(2,"0")).join("");
  }catch{ return null; }
}

/* Upload straight to the bucket with real byte progress. XHR, not fetch: fetch
   can't report upload progress. Plain request — our session headers are not
   part of what the presigned URL was signed for. */
function putWithProgress(url, headers, file, onPct){
  return new Promise((resolve,reject)=>{
    const xhr=new XMLHttpRequest();
    xhr.open("PUT", url, true);
    Object.entries(headers||{}).forEach(([k,v])=>xhr.setRequestHeader(k,v));
    xhr.upload.onprogress=e=>{ if(e.lengthComputable && onPct) onPct(e.loaded/e.total); };
    xhr.onload=()=> (xhr.status>=200 && xhr.status<300)
      ? resolve() : reject(new Error(`upload failed (${xhr.status})`));
    xhr.onerror=()=>reject(new Error("upload failed: network error"));
    xhr.send(file);
  });
}
