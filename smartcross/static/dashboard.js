const byId = id => document.getElementById(id);
const labels = {simulation: 'Simulação', webcam: 'Webcam', video: 'Vídeo local'};
const eventLabels = {ativacao:'LEDs acionados', desativacao:'LEDs desligados', entrada_roi:'Entrada na ROI', saida_roi:'Saída da ROI'};
const settingsForm = byId('settings');
const source = byId('source');
let state, streamRun, noticeTimer, lastEvent, sourceBusy = false;
let requestVersion = 0;

async function api(path, method = 'GET', data) {
  const options = {method, cache:'no-store'};
  if (data instanceof FormData) options.body = data;
  else if (data !== undefined) {
    options.headers = {'Content-Type':'application/json'};
    options.body = JSON.stringify(data);
  }
  const response = await fetch('/api/' + path, options);
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'A operação falhou.');
  return result;
}

function notice(message, error = false) {
  const target = byId('notice');
  target.textContent = message;
  target.className = error ? 'error' : '';
  target.hidden = false;
  clearTimeout(noticeTimer);
  noticeTimer = setTimeout(() => { target.hidden = true; }, 5000);
}

function sourceFields() {
  byId('camera-field').hidden = source.value !== 'webcam';
  byId('file-field').hidden = source.value !== 'video';
}

function settingsValues(values) {
  for (const [key, value] of Object.entries({...values, ...values.roi})) {
    if (key !== 'roi') settingsForm.elements[key].value = value;
  }
}

function render(next) {
  if (!state) {
    source.value = next.source;
    byId('camera').value = next.camera;
    sourceFields();
    settingsValues(next.settings);
  }
  if (next.error && state?.error !== next.error) notice(next.error, true);
  state = next;
  byId('system').textContent = next.status;
  byId('system').className = next.error ? 'danger' : next.running ? 'active' : '';
  byId('source-label').textContent = labels[next.source];
  const sim = next.source === 'simulation';
  byId('mode').textContent = sim ? 'SIMULAÇÃO' : 'YOLOv8n · CPU';
  byId('people').textContent = next.people;
  byId('inside').textContent = next.inside;
  byId('elapsed').textContent = next.elapsed.toLocaleString('pt-BR', {minimumFractionDigits:1}) + ' s';
  byId('fps').textContent = next.fps?.toLocaleString('pt-BR') ?? '—';
  byId('phase').textContent = next.phase;
  byId('phase').className = 'pill ' + (next.phase === 'ATIVA' ? 'active' : next.phase === 'INATIVA' ? '' : 'waiting');
  byId('crossing').classList.toggle('on', next.leds);
  byId('summary').textContent = next.inside ? next.inside + (sim ? ' na zona · presença simulada' : ' na zona de espera') : 'Zona vazia';
  byId('control').hidden = !sim;
  byId('count').disabled = !sim || next.status !== 'Em análise';
  if (!next.running) byId('count').value = '0';
  source.disabled = byId('camera').disabled = byId('file').disabled = next.running || sourceBusy;
  byId('start').disabled = next.running || sourceBusy;
  byId('stop').disabled = !next.running || next.status === 'Interrompendo' || sourceBusy;
  byId('scene').hidden = !sim;
  byId('placeholder').hidden = sim || next.stream_ready;
  byId('stream').hidden = !next.stream_ready;
  if (next.stream_ready && streamRun !== next.run_id) {
    byId('stream').src = '/api/stream?run=' + next.run_id;
    streamRun = next.run_id;
  } else if (!next.stream_ready && streamRun !== undefined) {
    byId('stream').removeAttribute('src');
    streamRun = undefined;
  }
  if (sim) drawScene(next);
}

function drawScene({settings, inside, leds}) {
  const canvas = byId('scene'), ctx = canvas.getContext('2d');
  const {width:w, height:h} = canvas;
  const box = (x,y,a,b,color) => { ctx.fillStyle = color; ctx.fillRect(x,y,a,b); };
  box(0,0,w,h,'#172737');
  box(0,88,w,174,'#202c39');
  box(0,80,w,8,'#50637a');
  box(0,262,w,8,'#50637a');
  for (let x=14;x<w;x+=46) if (x<270 || x>520) box(x,171,25,3,'#65768a');
  for (let x=289;x<520;x+=32) {
    box(x,92,17,166,'#d9e5ef');
    box(x,73,17,4,leds?'#61e6ac':'#526a83');
    box(x,273,17,4,leds?'#61e6ac':'#526a83');
  }
  const {x,y,width,height} = settings.roi;
  box(x*w,y*h,width*w,height*h,'#48dbfa22');
  ctx.strokeStyle='#4ad9fa'; ctx.lineWidth=2; ctx.setLineDash([8,5]);
  ctx.strokeRect(x*w,y*h,width*w,height*h); ctx.setLineDash([]);
  ctx.font='bold 18px system-ui'; ctx.fillStyle='#a9efff';
  ctx.fillText('SIMULAÇÃO', 20, 37);
  ctx.font='15px system-ui';
  ctx.fillText('ZONA DE ESPERA', Math.min(x*w+7,w-145), Math.max(y*h-7,58));
  for (let i=0;i<inside;i++) {
    const px=(x+width*(i+1)/(inside+1))*w, py=(y+height*.67)*h;
    ctx.fillStyle='#6be5b0';
    ctx.beginPath(); ctx.arc(px,py-20,7,0,Math.PI*2); ctx.fill();
    box(px-7,py-11,14,18,'#6be5b0');
  }
}

function renderHistory(stats, events) {
  byId('total').textContent = stats.total;
  const max = Math.max(1, ...stats.hours.map(hour => hour.count));
  const localHour = time => new Date(time).toLocaleTimeString('pt-BR',{hour:'2-digit',minute:'2-digit'});
  const bars = stats.hours.map(({time,count}) => {
    const bar = document.createElement('div');
    bar.className = 'bar';
    bar.style.height = Math.max(2,count/max*100) + '%';
    bar.title = localHour(time) + ' · ' + count + ' ativações';
    bar.setAttribute('aria-label',bar.title);
    return bar;
  });
  byId('chart').replaceChildren(...bars);
  byId('chart-labels').replaceChildren(...stats.hours.filter((_,i) => i%6===0 || i===23).map(({time}) => {
    const label = document.createElement('span'); label.textContent = localHour(time); return label;
  }));
  const list = byId('events');
  if (!events.length) list.textContent = 'Nenhum evento registrado.';
  else list.replaceChildren(...events.map(event => {
    const row=document.createElement('div'), title=document.createElement('b'), details=document.createElement('span');
    row.className='event';
    title.textContent=eventLabels[event.type] || event.type;
    details.textContent=new Date(event.timestamp).toLocaleString('pt-BR') + ' · ' + labels[event.source] + ' · ROI ' + event.people_in_roi;
    row.append(title,details); return row;
  }));
  if (lastEvent !== undefined && events.some(event => event.id > lastEvent && event.type === 'ativacao'))
    notice('Presença confirmada. LEDs virtuais acionados.');
  lastEvent = events[0]?.id ?? 0;
}

async function poll() {
  const version = requestVersion;
  try {
    const next = await api('state');
    if (version === requestVersion && !sourceBusy) render(next);
  } catch {
    byId('system').textContent = 'Conexão indisponível';
    byId('system').className = 'danger';
  } finally { setTimeout(poll, 500); }
}

async function history() {
  try { renderHistory(...await Promise.all([api('stats'),api('events')])); }
  catch { byId('events').textContent = 'Histórico temporariamente indisponível.'; }
  finally { setTimeout(history, 1500); }
}

source.addEventListener('change', sourceFields);
byId('source-form').addEventListener('submit', async event => {
  event.preventDefault();
  if (sourceBusy) return;
  const mode=source.value, camera=Number(byId('camera').value), file=byId('file').files[0];
  sourceBusy=true; requestVersion++;
  if (state) render(state);
  try {
    if (mode === 'video' && file) {
      const form=new FormData(); form.set('mode',mode); form.set('video',file);
      await api('source','POST',form);
      byId('file').value='';
    } else await api('source','POST',{mode,camera});
    render(await api('start','POST'));
  } catch (error) { notice(error.message,true); }
  finally { sourceBusy=false; requestVersion++; if (state) render(state); }
});
byId('stop').addEventListener('click', async () => {
  requestVersion++;
  try { render(await api('stop','POST')); } catch(error) { notice(error.message,true); }
});
byId('count').addEventListener('change', async event => {
  try { await api('simulation','POST',{count:Number(event.target.value)}); }
  catch(error) { notice(error.message,true); }
});
settingsForm.addEventListener('submit', async event => {
  event.preventDefault();
  const values = Object.fromEntries([...new FormData(settingsForm)].map(([key,value]) => [key, Number(value)]));
  const {x,y,width,height,...parameters}=values;
  try {
    settingsValues(await api('settings','PATCH',{...parameters,roi:{x,y,width,height}}));
    notice('Parâmetros aplicados.');
  } catch(error) { notice(error.message,true); }
});
for (const row of document.querySelectorAll('.leds')) {
  for (let index=0;index<8;index++) row.append(document.createElement('i'));
}
poll();
history();
