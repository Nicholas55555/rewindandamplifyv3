/* Offline view of frozen scientific outputs. No network calls or pretend live fitting. */
'use strict';
const $=id=>document.getElementById(id);
const palette={bg:'#102333',ink:'#f6f3eb',muted:'#b1c0cb',line:'#2b4253',cyan:'#64d9e9',amber:'#edb568',violet:'#b9a8e5',blue:'#7ea6c4'};
const D=window.DEMO_DATA;
const M=window.DiagnosticModel;
let selectedCase=0,replayTimer=null,walkTimer=null,step=0;
let coreModel='with_hidden_defect';
const reduced=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const baseProbability=0.0017263984682337737;
function textAt(ctx,s,x,y,size=14,color=palette.muted,align='left'){ctx.font=`${size}px "Segoe UI",Arial,sans-serif`;ctx.fillStyle=color;ctx.textAlign=align;ctx.fillText(s,x,y);}
function canvas(id){const el=$(id),ctx=el.getContext('2d');ctx.clearRect(0,0,el.width,el.height);return {el,ctx,w:el.width,h:el.height};}
function line(ctx,pts,color,width=2){if(!pts.length)return;ctx.beginPath();ctx.moveTo(...pts[0]);for(const p of pts.slice(1))ctx.lineTo(...p);ctx.strokeStyle=color;ctx.lineWidth=width;ctx.lineJoin='round';ctx.stroke();}
function roundRect(ctx,x,y,w,h,r=6){ctx.beginPath();ctx.roundRect(x,y,w,h,r);}
function drawResponse(){const df=+$('detuning').value,t2=+$('coherence').value,t=.02,p=M.ramseyProbability(df,t,t2);
 $('detuning-value').textContent=`${df.toFixed(1)} Hz`;$('coherence-value').textContent=`${t2.toFixed(2)} s`;$('response-value').innerHTML=`${(p*100).toFixed(1)}<span>%</span>`;
 const {ctx,w,h}=canvas('response-chart'),x0=35,x1=w-25,y0=15,y1=h-30;
 [0,.5,1].forEach(v=>{const y=y1-v*(y1-y0);line(ctx,[[x0,y],[x1,y]],palette.line,1);textAt(ctx,`${v*100}`,x0-8,y+4,12,palette.muted,'right');});
 const pts=[];for(let x=-15;x<=15.01;x+=.1)pts.push([x0+(x+15)/30*(x1-x0),y1-M.ramseyProbability(x,t,t2)*(y1-y0)]);line(ctx,pts,palette.cyan,3);
 const px=x0+(df+15)/30*(x1-x0),py=y1-p*(y1-y0);ctx.beginPath();ctx.arc(px,py,6,0,2*Math.PI);ctx.fillStyle=palette.amber;ctx.fill();
 textAt(ctx,'−15 Hz',x0,h-6,12);textAt(ctx,'0', (x0+x1)/2,h-6,12,palette.muted,'center');textAt(ctx,'+15 Hz',x1,h-6,12,palette.muted,'right');
}
function normRange(values,minSpan=1){const finite=values.filter(Number.isFinite);let lo=Math.min(...finite),hi=Math.max(...finite);if(!finite.length)return[-1,1];if(hi-lo<minSpan){const mid=(hi+lo)/2;lo=mid-minSpan/2;hi=mid+minSpan/2;}const pad=(hi-lo)*.13;return[lo-pad,hi+pad];}
function drawTrace(progress=1){const {ctx,w,h}=canvas('trace-chart');const c=D.scenarios[selectedCase];if(!c||!c.trace){textAt(ctx,D.status||'No frozen trace available.',25,50,18);return;}
 const tr=c.trace,tt=tr.time_s||[],n=tt.length,end=Math.max(1,Math.ceil(n*progress)),x0=63,x1=w-18;
 const rows=[{label:'SOURCE FREQUENCY',unit:'Hz',sets:[{v:tr.laser_frequency_hz,c:palette.ink,name:'known simulation truth'}],min:1},
 {label:'POWER MONITOR',unit:'relative',sets:[{v:tr.photodiode_relative_power,c:palette.amber,name:'photodiode'}],min:.01},
 {label:'FREQUENCY READOUTS',unit:'Hz',sets:[{v:tr.primary_heterodyne_hz,c:palette.violet,name:'primary coherent'},{v:tr.quantum_frequency_hz,c:palette.cyan,name:'atomic'},{v:tr.secondary_heterodyne_hz,c:palette.blue,name:'independent coherent'}],min:1}];
 const rowH=(h-35)/3;
 rows.forEach((row,i)=>{const top=i*rowH+28,bottom=(i+1)*rowH-14;const series=row.sets.filter(s=>s.v&&s.v.length);const [lo,hi]=normRange(series.flatMap(s=>s.v),row.min);
  textAt(ctx,row.label,x0,i*rowH+14,12,palette.muted);textAt(ctx,hi.toFixed(row.unit==='relative'?3:1),x0-10,top+6,12,palette.muted,'right');textAt(ctx,lo.toFixed(row.unit==='relative'?3:1),x0-10,bottom+3,12,palette.muted,'right');
  [0,.5,1].forEach(f=>line(ctx,[[x0,top+f*(bottom-top)],[x1,top+f*(bottom-top)]],palette.line,1));
  for(const s of series)line(ctx,s.v.slice(0,end).map((v,j)=>[x0+j/Math.max(1,n-1)*(x1-x0),bottom-(v-lo)/(hi-lo)*(bottom-top)]),s.c,i===2?1.9:2.2);
 });
 const last=tt[n-1]||128;textAt(ctx,'0 s',x0,h-6,12);textAt(ctx,`${last.toFixed(0)} s`,x1,h-6,12,palette.muted,'right');
 // Small persistent legend matches the three frequency traces.
 const labels=[['Primary coherent',palette.violet],['Atomic',palette.cyan],['Second coherent',palette.blue]];let x=x0+210;for(const [label,color]of labels){line(ctx,[[x,2*rowH+10],[x+16,2*rowH+10]],color,3);textAt(ctx,label,x+22,2*rowH+14,12,color);x+=label==='Primary coherent'?190:label==='Atomic'?110:150;}
}
function percent(v,digits=1){return (100*v).toFixed(digits)+'%';}
function renderBenchmark(){const c=D.scenarios[selectedCase];if(!c){$('case-title').textContent='Frozen evaluation not available';$('case-description').textContent=D.status||'No results loaded.';return;}
 $('case-title').textContent=c.label;$('case-description').textContent=c.description||'';
 const area=$('metrics');area.replaceChildren();
 (D.methods||[]).forEach((method,i)=>{const data=c.methods[method.id];if(!data)return;const div=document.createElement('div');div.className='metric';const title=document.createElement('div');title.className='metric-title';const label=document.createElement('span');label.textContent=method.label;const value=document.createElement('strong');value.textContent=percent(data.detection_rate);title.append(label,value);const track=document.createElement('div');track.className='bar-track';const fill=document.createElement('div');fill.className='bar-fill';fill.style.width=percent(data.detection_rate,4);fill.style.background=method.color||[palette.amber,palette.cyan,palette.violet,palette.blue][i%4];track.append(fill);const detail=document.createElement('small');let ci=data.detection_ci95;detail.textContent=`False alarms ${percent(data.false_alarm_rate)}${ci?` · detection 95% CI ${percent(ci[0])}–${percent(ci[1])}`:''}`;div.append(title,track,detail);area.append(div);});
 $('benchmark-note').textContent=D.benchmark_note||'Independent calibration and held-out synthetic records. Intervals describe Monte Carlo uncertainty in the specified model.';
 $('trace-note').textContent=c.trace_note||'One frozen simulated fault record. Hidden source truth is shown for explanation; estimators do not receive it. Color distinguishes frequency references.';
 $('finding').querySelector('p').textContent=c.finding||'Interpret the added channel against the independent conventional reference and its extra resources.';
 drawTrace();
}
function setupCases(){const select=$('case-select');select.replaceChildren();if(!D.scenarios.length){const opt=document.createElement('option');opt.textContent='Evidence bundle not yet available';select.append(opt);select.disabled=true;}else D.scenarios.forEach((c,i)=>{const opt=document.createElement('option');opt.value=i;opt.textContent=c.label;select.append(opt);});select.addEventListener('change',()=>{selectedCase=+select.value;stopReplay();renderBenchmark();});renderBenchmark();}
function stopReplay(){if(replayTimer)cancelAnimationFrame(replayTimer);replayTimer=null;$('replay').textContent='Replay trace';}
function replay(){if(replayTimer){stopReplay();drawTrace();return;}if(reduced){drawTrace();return;}const start=performance.now();$('replay').textContent='Show full trace';function tick(now){const p=Math.min(1,(now-start)/7000);drawTrace(p);if(p<1)replayTimer=requestAnimationFrame(tick);else stopReplay();}replayTimer=requestAnimationFrame(tick);}
const stageCaptions=[
 'Prepare a coherent model of possible histories, including information needed to reverse its dynamics.',
 'The oracle changes the phase of histories satisfying the selected event: a click in each time bin.',
 'Apply the inverse preparation circuit. Retained environment registers make the modeled evolution reversible.',
 'Reflect and prepare again. Each full round rotates amplitudes; too many rounds can overshoot. Ideal full amplification preserves the selected event’s conditional state.'
];
function highlightStep(s){step=s;document.querySelectorAll('.stage').forEach((el,i)=>{el.classList.toggle('active',i===s);el.setAttribute('aria-pressed',i===s);});$('stage-caption').textContent=stageCaptions[s];}
function setStep(s){highlightStep(s);$('iterations').value=s===3?'1':'0';updateAmplification();}
function updateAmplification(){const r=+$('iterations').value,p=M.amplifyProbability(baseProbability,r);$('iteration-value').textContent=r;$('amp-value').innerHTML=`${(100*p).toFixed(3)}<span>%</span>`;$('amp-label').textContent=r===0?'probability before amplification':`ideal probability after ${r} ${r===1?'round':'rounds'}`;$('gain').textContent=(p/baseProbability).toFixed(2)+'×';$('model-calls').textContent=2*r+1;
 const {ctx,w,h}=canvas('amplitude-chart'),x0=75,x1=w-35,y0=35,y1=h-60;
 [0,.25,.5,.75,1].forEach(f=>{const y=y1-f*(y1-y0);line(ctx,[[x0,y],[x1,y]],palette.line,1);textAt(ctx,(f*100)+'%',x0-15,y+5,16,palette.muted,'right');});
 textAt(ctx,'EVENT PROBABILITY',x0,18,13,palette.muted);
 const pts=Array.from({length:21},(_,i)=>[x0+i/20*(x1-x0),y1-M.amplifyProbability(baseProbability,i)*(y1-y0)]);line(ctx,pts,palette.cyan,3);pts.forEach(([x,y],i)=>{ctx.beginPath();ctx.arc(x,y,i===r?8:3,0,Math.PI*2);ctx.fillStyle=i===r?palette.amber:palette.cyan;ctx.fill();});
 [0,5,10,15,20].forEach(i=>textAt(ctx,i.toString(),x0+i/20*(x1-x0),h-30,15,palette.muted,'center'));textAt(ctx,'AMPLIFICATION ROUNDS',x1,h-5,12,palette.muted,'right');
 const px=pts[r][0],py=pts[r][1];line(ctx,[[px,y1],[px,py]],palette.amber,1);textAt(ctx,percent(p,2),M.clamp(px+15,x0,x1-75),M.clamp(py-15,y0+5,y1-18),19,palette.amber);
}
function stopWalk(){if(walkTimer)clearInterval(walkTimer);walkTimer=null;$('walk').textContent='Play the explanation';}
function walkthrough(){if(walkTimer){stopWalk();return;}setStep(0);$('walk').textContent='Pause explanation';walkTimer=setInterval(()=>{if(step>=3){stopWalk();return;}setStep(step+1);},4500);}
function drawFingerprint(){
 const source=D.original;if(!source)throw new Error('Original QRSM evidence bundle is missing');
 const model=source.models[coreModel],variant=$('core-method').value,answer=model.ideal_circuits[variant];
 const coupled=coreModel==='with_hidden_defect',color=coupled?palette.cyan:palette.amber;
 $('core-coupled').setAttribute('aria-pressed',coupled);$('core-emitter').setAttribute('aria-pressed',!coupled);
 $('core-acceptance').textContent=percent(answer.event_probability,2);$('core-acceptance').style.color=color;$('core-acceptance-bar').style.width=percent(answer.event_probability,5);$('core-acceptance-bar').style.background=color;
 const error=answer.max_conditional_error*100;
 $('core-error').textContent=error<.0001?'<0.0001 percentage points':error.toFixed(4)+' percentage points';
 $('core-error').style.color=error>.1?palette.amber:palette.ink;
 const {ctx,w,h}=canvas('fingerprint-chart'),x0=85,x1=w-60,y0=38,y1=h-65;
 [0,.04,.08,.12].forEach(v=>{const y=y1-v/.14*(y1-y0);line(ctx,[[x0,y],[x1,y]],palette.line,1);textAt(ctx,`${Math.round(v*100)}%`,x0-16,y+6,17,palette.muted,'right');});
 textAt(ctx,'CHANCE OF A LATER CLICK, GIVEN A CLICK AT STEP 3',x0,17,14,palette.muted);
 const toPoints=values=>values.map((v,j)=>[x0+(j+.15)/2.3*(x1-x0),y1-v/.14*(y1-y0)]);
 ctx.setLineDash([7,6]);line(ctx,toPoints(model.exact_conditional_probabilities),palette.muted,2.5);ctx.setLineDash([]);
 const points=toPoints(answer.conditional_probabilities);line(ctx,points,color,3.5);
 points.forEach(([x,y],i)=>{ctx.beginPath();ctx.arc(x,y,7,0,Math.PI*2);ctx.fillStyle=color;ctx.fill();textAt(ctx,percent(answer.conditional_probabilities[i],2),x,y-20,22,color,'center');textAt(ctx,`Step ${source.event.future_steps[i]}`,x,h-28,19,palette.ink,'center');});
 const readable=$('core-future-values');readable.replaceChildren();answer.conditional_probabilities.forEach((value,i)=>{const cell=document.createElement('div'),label=document.createElement('small'),number=document.createElement('strong');label.textContent=`Step ${source.event.future_steps[i]}`;number.textContent=percent(value,2);number.style.color=color;cell.append(label,number);readable.append(cell);});
 textAt(ctx,'Solid: selected circuit. Dashed: exact model target.',x0,h-4,13,palette.muted);
 const modelLabel=coupled?'coupled hidden-memory':'emitter-only';
 $('fingerprint-note').textContent=`The ${modelLabel} model is deliberately programmed. Frozen ideal Qiskit results, checked against exact filtering. Steps have no calibrated physical duration.`;
 const exactLast=model.exact_conditional_probabilities[2],last=answer.conditional_probabilities[2];
 let finding;
 if(variant==='plain')finding=`Plain sampling keeps ${percent(model.original_event_probability,2)} of this model’s runs. The useful answer is the later pattern, including ${percent(exactLast,2)} at step 6.`;
 else if(variant==='full_steered')finding=`Steering + full amplification raises acceptance from ${percent(model.original_event_probability,2)} to ${percent(answer.event_probability,2)}. The step-6 answer stays ${percent(exactLast,2)} within numerical precision.`;
 else if(variant==='local_steered')finding=`The smaller local-reflection circuit accepts ${percent(answer.event_probability,2)} of runs in this ideal test. Its largest future-answer error is ${error<.0001?'<0.0001':error.toFixed(4)} percentage points.`;
 else finding=coupled?'This control happens to stay close for the coupled model here. Switch to “Emitter only” to see why an accuracy check across models matters.':`This control keeps ${percent(answer.event_probability,2)} of runs but changes the step-6 answer from ${percent(exactLast,2)} to ${percent(last,2)}. Many accepted runs can still give the wrong answer.`;
 $('core-finding').textContent=finding;
 const job=source.hardware_jobs[0],plain=job.rows.find(r=>r.model_id==='with_hidden_defect'&&r.variant==='plain'),local=job.rows.find(r=>r.model_id==='with_hidden_defect'&&r.variant==='local_steered');
 $('core-hardware-note').textContent=`The archived longer coupled-model query kept ${plain.raw_selected_count.toLocaleString()} plain versus ${local.raw_selected_count.toLocaleString()} amplified histories from ${local.shots.toLocaleString()} shots. Layouts and circuit depths differ; these are programmed models.`;
}
function activateTab(id){document.querySelectorAll('.tab').forEach(el=>{const active=el.dataset.tab===id;el.classList.toggle('active',active);el.setAttribute('aria-selected',active);el.tabIndex=active?0:-1;});document.querySelectorAll('.chapter').forEach(el=>el.hidden=el.id!==id);stopReplay();stopWalk();if(id==='rewind'){drawFingerprint();updateAmplification();}if(id==='sensor'){drawResponse();drawTrace();}history.replaceState(null,'','#'+id);}
document.querySelectorAll('.tab').forEach(el=>el.addEventListener('click',()=>activateTab(el.dataset.tab)));
$('open-current-research').addEventListener('click',()=>{window.ResearchUI.show('frequency');activateTab('research');$('study-frequency').focus();});
document.querySelector('.tabs').addEventListener('keydown',e=>{if(e.ctrlKey||e.metaKey||e.altKey)return;const tabs=Array.from(document.querySelectorAll('.tab'));const at=tabs.indexOf(document.activeElement);if(at<0)return;let next=at;if(e.key==='ArrowRight')next=(at+1)%tabs.length;else if(e.key==='ArrowLeft')next=(at+tabs.length-1)%tabs.length;else if(e.key==='Home')next=0;else if(e.key==='End')next=tabs.length-1;else return;e.preventDefault();activateTab(tabs[next].dataset.tab);tabs[next].focus();});
document.querySelectorAll('.stage').forEach(el=>el.addEventListener('click',()=>{stopWalk();setStep(+el.dataset.step);}));
$('core-coupled').addEventListener('click',()=>{coreModel='with_hidden_defect';drawFingerprint();});$('core-emitter').addEventListener('click',()=>{coreModel='no_hidden_defect';drawFingerprint();});$('core-method').addEventListener('change',drawFingerprint);
$('detuning').addEventListener('input',drawResponse);$('coherence').addEventListener('input',drawResponse);$('iterations').addEventListener('input',()=>{stopWalk();highlightStep(+$('iterations').value>0?3:0);updateAmplification();});$('replay').addEventListener('click',replay);$('walk').addEventListener('click',walkthrough);
$('motion').addEventListener('click',()=>{const active=$('motion').getAttribute('aria-pressed')!=='true';$('motion').setAttribute('aria-pressed',active);$('motion').textContent=active?'Pause light path':'Play light path';document.querySelector('.optical-diagram').classList.toggle('moving',active);});
$('present').addEventListener('click',()=>{const active=document.body.classList.toggle('focus-view');$('present').textContent=active?'Full view':'Focus view';$('present').setAttribute('aria-pressed',active);});
if(new URLSearchParams(location.search).get('focus')==='1'){document.body.classList.add('focus-view');$('present').textContent='Full view';$('present').setAttribute('aria-pressed','true');}
if(reduced){$('motion').disabled=true;$('motion').textContent='Reduced motion';$('replay').disabled=true;$('replay').textContent='Full trace shown';$('walk').disabled=true;$('walk').textContent='Choose a step';}
drawResponse();setupCases();setStep(0);activateTab(['research','sensor','rewind','evidence'].includes(location.hash.slice(1))?location.hash.slice(1):'rewind');
window.addEventListener('beforeunload',()=>{stopReplay();stopWalk();});
