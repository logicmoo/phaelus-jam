
    async function fetchPorts(){ return await fetch('/api/ports').then(r=>r.json()); }
    async function selectPorts(inp,outp){ const p=new URLSearchParams({in_name:inp,out_name:outp}); return await fetch('/api/start?'+p.toString(),{method:'POST'}).then(r=>r.json()); }
    async function applyParams(){ const roleSwap=document.getElementById('roleSwap').checked; const density=document.getElementById('density').value; const model=document.getElementById('model').value; const p=new URLSearchParams(); p.set('role_swap', roleSwap); p.set('density', density); if(model) p.set('model', model); return await fetch('/api/params?'+p.toString(),{method:'POST'}).then(r=>r.json()); }

    function setLed(id,on,kind='ok'){ const el=document.getElementById(id); if(!el) return; el.className='led'+(on?(' on '+kind):''); }
    function updateLEDs(s){ setLed('led-midi-in', !!s.midi_in_connected,'ok'); setLed('led-midi-out', !!s.midi_out_connected,'ok'); setLed('led-engine', !!s.engine_running,'info'); setLed('led-llm', !!s.llm_enabled,'ok'); }

    async function fetchMetrics(){ return await fetch('/api/metrics').then(r=>r.json()); }
    function updateStats(cm){ if(!cm) return; const set=(id,val)=>{ const el=document.getElementById(id); if(el) el.textContent=val; }; set('m-llm-req', cm.llm_req??0); set('m-tok-in', cm.tok_in??0); set('m-tok-out', cm.tok_out??0); set('m-midi-in', cm.midi_in??0); set('m-midi-out', cm.midi_out??0); set('m-late', (cm.late_pct??0)+'%'); }

    function ts(){ return new Date().toISOString().replace('T',' ').replace('Z',''); }
    function logMsg(kind,obj){ const box=document.getElementById('logBox'); if(!box) return; const doWs=document.getElementById('logWs')?.checked ?? true; const doHttp=document.getElementById('logHttp')?.checked ?? false; if((kind==='ws'&&!doWs)||(kind==='http'&&!doHttp)) return; const line=`[${ts()}] ${kind.toUpperCase()} ${typeof obj==='string'?obj:JSON.stringify(obj)}`; box.textContent += (box.textContent?'
':'')+line; box.scrollTop=box.scrollHeight; }

    function updatePreview(){ const presetText=document.getElementById('presetText').value.trim(); const appendText=document.getElementById('appendText').value.trim(); const preview=(presetText?("Preset: "+presetText+"
"):"")+(appendText?("User: "+appendText):""); document.getElementById('promptPreview').textContent = preview || "(no extra guidance)"; }
    async function applyPrompt(){ const presetText=document.getElementById('presetText').value; const appendText=document.getElementById('appendText').value; const p=new URLSearchParams(); p.set('preset_text', presetText); p.set('append_text', appendText); await fetch('/api/params?'+p.toString(),{method:'POST'}); }

    async function fetchPresetFiles(){ return await fetch('/api/preset_files').then(r=>r.json()); }
    async function mergeSelectedFiles(){ const selected=Array.from(document.querySelectorAll('#fileBox input[type=checkbox]:checked')).map(x=>x.value); const p=new URLSearchParams(); p.set('files', JSON.stringify(selected)); const pdata=await fetch('/api/merge_presets?'+p.toString(),{method:'POST'}).then(r=>r.json()); window.__PRESET_DATA__=pdata; const sel=document.getElementById('presetSel'); sel.innerHTML=""; (pdata.presets||[]).forEach(p=>{ const o=document.createElement('option'); o.value=p.name; o.textContent=p.name; sel.appendChild(o); }); if((pdata.presets||[]).length){ sel.value=pdata.presets[0].name; document.getElementById('presetText').value=pdata.presets[0].text||""; } else { document.getElementById('presetText').value=""; } updatePreview(); renderBoosters(pdata); await initPresetFiles(); }

    async function uploadPresetFile(){ const inp=document.getElementById('uploadInput'); if(!inp.files||!inp.files[0]) return; const fd=new FormData(); fd.append('file', inp.files[0]); const res=await fetch('/api/presets/upload',{method:'POST', body:fd}); if(res.ok){ await initPresetFiles(); inp.value=""; } else { const j=await res.json().catch(()=>({detail:'Upload failed'})); alert(j.detail||'Upload failed'); } }

    function renderBoosters(pdata){ const box=document.getElementById('boostersBox'); if(!box) return; box.innerHTML="<label>Style Boosters:</label>"; (pdata.boosters||[]).forEach(b=>{ const id="booster_"+b.key; const wrap=document.createElement('div'); wrap.className='row'; const cb=document.createElement('input'); cb.type='checkbox'; cb.id=id; cb.value=b.key; const lab=document.createElement('label'); lab.htmlFor=id; lab.textContent=" "+b.label; wrap.appendChild(cb); wrap.appendChild(lab); box.appendChild(wrap); }); }
    async function initPresetFiles(){ const files=await fetchPresetFiles(); const box=document.getElementById('fileBox'); box.innerHTML=""; (files.files||[]).forEach(fileObj=>{ const fn=(fileObj.name||fileObj); const id="file_"+fn.replace(/[^a-zA-Z0-9_.-]/g,"_"); const wrap=document.createElement('div'); wrap.className='row'; const cb=document.createElement('input'); cb.type='checkbox'; cb.id=id; cb.value=fn; const lab=document.createElement('label'); lab.htmlFor=id; lab.textContent=" "+fn; const a=document.createElement('a'); a.href='/api/presets/download?name='+encodeURIComponent(fn); a.textContent=' (download)'; a.style.marginLeft='8px'; a.target='_blank'; const st=document.createElement('span'); st.className='status'; const s=(fileObj.status||'unloaded'); const msg=(fileObj.message||''); st.textContent=' ['+s+(msg?(': '+msg):'')+']'; st.dataset.status=s; wrap.appendChild(cb); wrap.appendChild(lab); wrap.appendChild(a); wrap.appendChild(st); box.appendChild(wrap); }); const rc=document.getElementById('reloadChanged'); if(rc) rc.disabled = !anyModified(); document.getElementById('loadSelected').addEventListener('click', mergeSelectedFiles); document.getElementById('reloadFiles').addEventListener('click', initPresetFiles); document.getElementById('exportSelected').addEventListener('click', async ()=>{ const selected=Array.from(document.querySelectorAll('#fileBox input[type=checkbox]:checked')).map(x=>x.value); const name=document.getElementById('exportName').value; const p=new URLSearchParams(); p.set('files', JSON.stringify(selected)); if(name) p.set('filename', name); const j=await fetch('/api/export_presets?'+p.toString(),{method:'POST'}).then(r=>r.json()); if(j.ok){ await initPresetFiles(); alert('Exported: '+j.name); } }); document.getElementById('uploadBtn').addEventListener('click', uploadPresetFile); }
    function anyModified(){ return Array.from(document.querySelectorAll('#fileBox span.status')).some(st=>st.dataset.status==='modified'); }
    async function reloadChanged(){ await fetch('/api/reload_changed',{method:'POST'}); await initPresetFiles(); }

    function initTabs(){ const tabs=document.querySelectorAll('#tabbar .tab'); const panels=document.querySelectorAll('#panels .panel'); tabs.forEach(btn=>{ btn.addEventListener('click', ()=>{ tabs.forEach(b=>b.classList.remove('active')); panels.forEach(p=>p.classList.remove('active')); btn.classList.add('active'); document.getElementById(btn.dataset.panel).classList.add('active'); }); }); }

    function initLogPanel(){ const clr=document.getElementById('clearLog'); const dl=document.getElementById('downloadLog'); if(clr) clr.addEventListener('click', ()=>{ document.getElementById('logBox').textContent=''; }); if(dl) dl.addEventListener('click', ()=>{ const blob=new Blob([document.getElementById('logBox').textContent],{type:'text/plain'}); const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download='phaelusjam-log.txt'; a.click(); }); }
    function initTesting(){ const tr=(id,fn)=>{ const el=document.getElementById(id); if(el) el.addEventListener('click', fn); }; tr('btnPing', async()=>{ const j=await fetch('/api/ports').then(r=>r.json()); document.getElementById('testResult').textContent=JSON.stringify(j,null,2); }); tr('btnSuggest',()=>{ if(window.__WS__&&window.__WS__.readyState===1){ const m=JSON.stringify({type:'suggest_now'}); logMsg('ws',{direction:'send',data:m}); window.__WS__.send(m);} }); tr('btnFetchPorts', async()=>{ const j=await fetch('/api/ports').then(r=>r.json()); document.getElementById('testResult').textContent=JSON.stringify(j,null,2); }); tr('btnApplyParamsQuick', async()=>{ const p=new URLSearchParams({role_swap:true, density:3}); const j=await fetch('/api/params?'+p.toString(),{method:'POST'}).then(r=>r.json()); document.getElementById('testResult').textContent=JSON.stringify(j,null,2); }); const fm=document.getElementById('btnFetchMetrics'); if(fm) fm.addEventListener('click', async()=>{ const m=await fetchMetrics(); document.getElementById('testResult').textContent=JSON.stringify(m,null,2); }); const rm=document.getElementById('btnResetMetrics'); if(rm) rm.addEventListener('click', async()=>{ await fetch('/api/metrics/reset',{method:'POST'}); const m=await fetchMetrics(); document.getElementById('testResult').textContent=JSON.stringify(m,null,2); }); }
    function initAiToggle(){ const t=document.getElementById('aiToggle'); if(!t) return; const apply=async()=>{ const p=new URLSearchParams({use_llm:t.checked}); await fetch('/api/params?'+p.toString(),{method:'POST'}); }; t.addEventListener('change', apply); }

    function connectWS(){
      const ws = new WebSocket(`ws://${location.host}/ws`); window.__WS__=ws; setLed('led-ws', false);
      ws.addEventListener('open', ()=> setLed('led-ws', true, 'info'));
      ws.addEventListener('close', ()=> setLed('led-ws', false));
      ws.addEventListener('error', ()=> setLed('led-ws', false));
      ws.addEventListener('message', (ev)=>{ logMsg('ws',{direction:'recv', data: ev.data}); try{ var data=JSON.parse(ev.data);}catch(_){return;}
        if(data.type==='files_update'){ const box=document.getElementById('fileBox'); const map={}; (data.files||[]).forEach(f=>map[f.name]=f); (box.querySelectorAll('div.row')||[]).forEach(row=>{ const label=row.querySelector('label'); if(!label) return; const name=(label.textContent||'').trim(); const st=row.querySelector('span.status'); if(!st) return; const f=map[name]; if(!f) return; st.dataset.status=f.status||'unloaded'; st.textContent=' ['+(f.status||'unloaded')+(f.message?(': '+f.message):'')+']'; }); const btn=document.getElementById('reloadChanged'); if(btn) btn.disabled = !anyModified(); return; }
        if(data.type==='state'){ updateLEDs(data); updateStats(data.compact_metrics); const bpm=document.getElementById('bpm'); if(bpm) bpm.textContent=data.bpm; const held=document.getElementById('held'); if(held) held.textContent=JSON.stringify(data.held); const recent=document.getElementById('recent'); if(recent) recent.textContent=JSON.stringify(data.recent_notes); const vel=data.recent_velocities||[]; const intensity = vel.length? Math.round(vel.reduce((a,b)=>a+b,0)/vel.length):0; const intenEl=document.getElementById('intensity'); if(intenEl) intenEl.textContent = intensity; const t=document.getElementById('aiToggle'); if(t) t.checked = !!data.llm_enabled; }
      });
      setInterval(()=>{ if(ws.readyState===1){ const msg=JSON.stringify({type:'tick'}); logMsg('ws',{direction:'send', data: msg}); ws.send(msg);} }, 500);
    }

    async function init(){
      const ports=await fetchPorts(); const inSel=document.getElementById('inSel'); const outSel=document.getElementById('outSel');
      ports.inputs.forEach(n=>{ const o=document.createElement('option'); o.value=n; o.textContent=n; inSel.appendChild(o); });
      ports.outputs.forEach(n=>{ const o=document.createElement('option'); o.value=n; o.textContent=n; outSel.appendChild(o); });
      document.getElementById('startBtn').addEventListener('click', async()=>{ const res=await selectPorts(inSel.value, outSel.value); console.log('Started.', res); });
      document.getElementById('applyParams').addEventListener('click', async()=>{ const res=await applyParams(); console.log('Params applied:', res); });
      connectWS(); initTabs(); initPresetFiles(); initLogPanel(); initTesting(); initAiToggle();

      // prompts preset UI
      const sel=document.getElementById('presetSel'); const boostersBox=document.createElement('div'); boostersBox.id='boostersBox'; boostersBox.className='row'; document.getElementById('prompts').appendChild(boostersBox);
      const pdata = await fetch('/api/presets').then(r=>r.json()).catch(()=>({presets:[],boosters:[]})); window.__PRESET_DATA__=pdata;
      (pdata.presets||[]).forEach(p=>{ const o=document.createElement('option'); o.value=p.name; o.textContent=p.name; sel.appendChild(o); });
      sel.addEventListener('change', ()=>{ const p=(window.__PRESET_DATA__.presets||[]).find(x=>x.name===sel.value); document.getElementById('presetText').value = p ? p.text : ""; updatePreview(); });
      if((pdata.presets||[]).length){ sel.value=pdata.presets[0].name; document.getElementById('presetText').value=pdata.presets[0].text||""; }
      document.getElementById('appendText').addEventListener('input', updatePreview);
      document.getElementById('presetText').addEventListener('input', updatePreview);
      document.getElementById('applyPrompt').addEventListener('click', applyPrompt);
      renderBoosters(pdata); updatePreview();
    }
    init();
