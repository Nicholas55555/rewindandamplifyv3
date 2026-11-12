import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL,fileURLToPath} from 'node:url';
import {Presentation,PresentationFile} from '@oai/artifact-tool';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..').replaceAll('\\','/');
const build=root+'/.finals-deck-build';
process.env.RUNTIME_NODE_MODULES??=await fs.realpath(path.join(build,'node_modules'));
const skill=process.env.PRESENTATIONS_SKILL_DIR??'C:/Users/nicho/.codex/plugins/cache/openai-primary-runtime/presentations/26.1105.12137/skills/presentations';
const py=process.env.RUNTIME_PYTHON??'C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1105-1297-0_26.1105.1297.0_x64__3k8sg7r9htsxt/dependencies/python/python.exe';
const draft=process.argv.includes('--draft');
const C={navy:'#091624',cream:'#F6F3EB',cyan:'#64D9E9',amber:'#EDB568',ink:'#11283B',teal:'#147D8C',ochre:'#9C5F15',muted:'#566875',light:'#AABCC7',line:'#D7DFDF',slate:'#344A5C'};
const P=Presentation.create({slideSize:{width:1280,height:720}});
const {applyPresentationChartFont,finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
const scripts=[];
function txt(s,t,x,y,w,h,size=28,color=C.ink,bold=false,align='left'){
 const q=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 q.text=t;q.text.style={typeface:'Arial',fontSize:size,color,bold,alignment:align,verticalAlignment:'middle',wrap:'square',autoFit:'shrinkText',insets:0};return q;
}
function slide(title,n,dark=false){const s=P.slides.add();s.background.fill=dark?C.navy:C.cream;
 if(title)txt(s,title,64,45,1152,80,42,dark?C.cream:C.ink,true);
 txt(s,String(n).padStart(2,'0'),1160,671,56,20,14,dark?C.light:C.muted,false,'right');return s;}
function footer(s,t,dark=false){txt(s,t,64,628,1100,39,17,dark?C.light:C.muted);}
async function img(s,p,x,y,w,h,alt,fit='contain'){const b=await fs.readFile(p);s.images.add({blob:b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength),contentType:/\.gif$/i.test(p)?'image/gif':/\.jpe?g$/i.test(p)?'image/jpeg':'image/png',alt,fit,position:{left:x,top:y,width:w,height:h}});}
function readable(t){return t.replace(/([a-z])(\d)/g,'$1 $2').replace(/(\d)([A-Za-z])/g,'$1 $2').replace(/:(?=\d)/g,': ').replaceAll('outof','out of').replaceAll('CZgates','CZ gates').replaceAll('nativeCZ','native CZ').replaceAll('haveTV','have TV').replaceAll('throughN','through N').replaceAll('adaptiveBBHT','adaptive BBHT').replaceAll('%interval','% interval').replaceAll('A20','A 20');}
function note(s,title,time,text,sources,cue=''){text=readable(text);cue=readable(cue);s.speakerNotes.text=`${time}\n\n${text}\n\nPRESENTER CUE: ${cue}\n\nSOURCES: ${sources}`;scripts.push({title,time,text,sources,cue});}
function chart(s,type,opt){const c=s.charts.add(type,opt);applyPresentationChartFont(c,{fontFamily:'Arial'});return c;}
function table(s,values,widths,top=180,height=350,size=24){const t=s.tables.add({rows:values.length,columns:values[0].length,left:64,top,width:1152,height,columnWidths:widths,values});
 t.borders.assign({fill:C.line,width:0.7,style:'solid'});
 for(let r=0;r<values.length;r++)for(let c=0;c<values[r].length;c++){let q=t.getCell(r,c);q.fill=r===0?C.navy:C.cream;q.text.style={typeface:'Arial',fontSize:size,color:r===0?C.cream:C.ink,bold:r===0,verticalAlignment:'middle',wrap:'square',insets:12};}
 return t;
}
const summ=JSON.parse(await fs.readFile(root+'/rewindandamplify-main/results/hardware/summary_plain.json','utf8'));
const exactP=summ.rows.find(r=>r.name==='click3-full-r0').raw.ideal_hit;
const full=summ.rows.find(r=>r.name==='click3-steered-full-r1');
const local=summ.rows.find(r=>r.name==='click3-steered-memory+last-1-r1');

// This file is inserted into visual_build.mjs by visual_revise_v3.py.
// Main talk: 13 slides, 9:20 including a 45-second demonstration.
const after=JSON.parse(await fs.readFile(root+'/research-validation/original_after_click_verification.json','utf8'));
const evidence=JSON.parse(await fs.readFile(root+'/laser_sensor_viability/results.json','utf8'));
const sensorNow=JSON.parse(await fs.readFile(root+'/laser_sensor_viability/followup/main/results.json','utf8'));
const driveNow=JSON.parse(await fs.readFile(root+'/qrsm_photon_poc/drive_diagnostics_followup/main/results.json','utf8'));
const phaseNow=JSON.parse(await fs.readFile(root+'/quantum_lithography_poc/phase_inspection_followup/results.json','utf8'));
const spatialNow=JSON.parse(await fs.readFile(root+'/finals-lithography/full_spatial_circuit/results.json','utf8'));
const exposureNow=JSON.parse(await fs.readFile(root+'/quantum_lithography_poc/exposure_followup/results.json','utf8'));
const dotBridge=JSON.parse(await fs.readFile(root+'/quantum_dot_bridge/results.json','utf8'));
const homAnalysis=JSON.parse(await fs.readFile(root+'/quantum_dot_bridge/hom_analysis/results.json','utf8'));
const campaignNow=JSON.parse(await fs.readFile(root+'/hardware_campaign/results.json','utf8'));
const campaignRun=async id=>JSON.parse(await fs.readFile(root+'/'+campaignNow.runs.find(r=>r.id===id).analysis_path,'utf8'));
const hwPrecision=await campaignRun('original_precision_v1');
const hwHero=JSON.parse(await fs.readFile(root+'/hardware_campaign/runs/original_precision_v1/hero_acceptance_contrast.json','utf8'));
const hwLoops=JSON.parse(await fs.readFile(root+'/hardware_campaign/runs/original_precision_v1/loop_contrasts.json','utf8'));
const hwFirst=await campaignRun('original_plain_v2');
const hwSuppressed=await campaignRun('original_suppressed_v1');
const hwOptical=await campaignRun('optical_dilation_plain_v2');
const hwChannels=await campaignRun('optical_controls_plain_v1');
const hwDots=await campaignRun('dots_plain_v1');
const dotStudy=JSON.parse(await fs.readFile(root+'/quantum_dot_bridge/qrsm_hom_followup/main/results.json','utf8'));
const dotDesign=JSON.parse(await fs.readFile(root+'/quantum_dot_bridge/qrsm_hom_followup/exploratory_design/validation_run/results.json','utf8'));
const pct=(v,places=1)=>(100*v).toFixed(places)+'%';
{
 const s=slide('',1,true);
 await img(s,root+'/finals-deck/assets/optical-cover.png',0,0,1280,720,'Conceptual optical interference artwork, not an apparatus','cover');
 txt(s,'Rewind &\nAmplify',64,115,800,200,78,C.cream,true);
 txt(s,'Predicting how hidden defects change\nquantum measurement patterns',68,335,1030,100,34,C.light);
 txt(s,'A Qiskit model tested on IBM hardware.\nExploratory extension: laser diagnostics.',68,454,1000,85,27,C.cream);
 txt(s,'Qubits  /  Florida Gulf Coast University',68,569,1000,37,23,C.cyan,true);
 txt(s,'Florida Qiskit Hackathon finals  /  FAU  /  14 November 2026',68,623,1100,35,18,C.light);
 note(s,'Rewind & Amplify','0:00–0:15',
 'We are Qubits from Florida Gulf Coast University. We model how hidden defects change quantum measurement patterns, then test a method for querying that model on IBM hardware. Laser diagnosis is a separate research extension.',
 'Original project README and docs/REPORT.md. Event: https://entangledsolutionsgroup.com/Qiskit-Fall-Fest-2026/. Conceptual cover generated with OpenAI image generation.',
 'Nicholas introduces the problem. First nine slides cover the original quantum computation.');
}

{
 const s=slide('Hidden defects can change the state before readout',2);
 txt(s,'State estimates depend on the dynamics and readout model',64,137,1152,50,29,C.ink);
 txt(s,'During qubit evolution',64,223,540,45,32,C.teal,true);
 txt(s,'A coupled defect can exchange energy\nor change the qubit’s frequency.',64,289,540,95,28,C.ink);
 txt(s,'The intended state can evolve\ndifferently from the ideal circuit.',64,417,540,82,27,C.muted);
 txt(s,'When interpreting the readout',724,223,492,45,30,C.ochre,true);
 txt(s,'Repeated measurements estimate\nprobabilities, not a full state in one shot.',724,289,492,95,28,C.ink);
 txt(s,'Readout errors and hidden dynamics\ncan otherwise receive the wrong explanation.',724,417,492,82,27,C.muted);
 txt(s,'Potential value: better calibration and more trustworthy state estimates',64,547,1152,68,30,C.ink,true);
 footer(s,'State estimation needs appropriate measurements and a validated noise model. This project has not diagnosed a physical defect.');
 note(s,'Hidden defects can change the state before readout','0:15–1:00',
 'Why analyze defects? A hidden two-level system can exchange energy with a qubit or shift its frequency. Then the state evolves differently from the ideal circuit. We infer quantum behavior from repeated preparations and measurements. One readout does not reveal an arbitrary full quantum state. If our analysis ignores hidden dynamics or detector errors, we can assign the wrong cause to the observed statistics. Defect analysis can inform calibration, operating frequencies and device selection, helping preserve useful computation and interpret state estimates. Our project tests a modeling approach to that analysis. It has not diagnosed an unknown physical defect or performed complete state tomography.',
 'Schlor et al., PRL123190502 (2019): https://www.nist.gov/publications/correlating-decoherence-transmon-qubits-low-frequency-noise-single-fluctuators. Keith et al., PRA98042318 (2018): https://www.nist.gov/publications/joint-quantum-state-and-measurement-tomography-incomplete-measurements. These support the physical context and measurement-inference limitations, not validation of our surrogate. Local mechanism: original prior_work/hidden_defects/README.md and qrsm_grover/model.py.',
 'Nicholas distinguishes physical state evolution from inference about that state. The QRSM models possible causes of the record.');
}
// WHAT QRSM ADDS BEFORE GROVER

{
 const s=slide('A click is one recorded measurement outcome',3);
 txt(s,'1 = click',64,157,530,76,58,C.teal,true);
 txt(s,'The output qubit reads 1\nin one model time step.',67,249,540,85,29,C.ink);
 txt(s,'0 = no click',742,161,470,65,45,C.muted,true);
 txt(s,'A single click does not\nidentify a defect.',744,249,455,85,29,C.ink);
 table(s,[['Time step','1','2','3','4'],['One example record','0','0','1','0']],[432,180,180,180,180],380,134,30);
 txt(s,'The emitter and hidden qubit carry memory between steps',64,546,1152,62,29,C.ink,true);
 footer(s,'Optical interpretation: a detector fires. On IBM, superconducting qubits represent this model.');
 note(s,'A click is one recorded measurement outcome','1:00–1:35',
 'A click means the model output reads one in a time step. Zero means no click. This example reads zero, zero, one, zero: a click at step three. Our query selects that step alone and allows any earlier history. Optically, the bit represents a detector firing. On IBM, a superconducting qubit represents that output. The emitter and hidden qubit carry memory to the next step. This repeating model is a quantum recurrent state machine, or QRSM.',
 'rewindandamplify-main/qrsm_grover/model.py: QRSM.dynamic, QRSM.purified, history_to_string. Original deck circuit slide and docs/TEAM_GUIDE.md. Example0010 is illustrative chronological notation, not a Qiskit endian-formatted counts key.',
 'Trace the four columns left to right. Say “a recorded one,” before using “click” again.');
}

{
 const s=slide('The QRSM connects each bit to a hidden-state model',4);
 txt(s,'Does an emitter alone explain the record, or does a hidden partner help?',64,136,1152,52,29,C.ink);
 txt(s,'Updates the modeled state',64,222,570,43,31,C.teal,true);
 txt(s,'Each observed 0 or 1 updates the\nconditional state of the emitter\nand its hidden partner.',64,289,570,126,30,C.ink);
 txt(s,'Scores a physical explanation',724,222,492,43,30,C.ochre,true);
 txt(s,'Candidate coupling and noise settings\nassign a probability to the record\nand predict the next readout.',724,289,492,126,28,C.ink);
 txt(s,'A fresh synthetic test: detector dead time changes the inferred coupling',64,452,1152,49,27,C.ink,true);
 table(s,[['True coupling','Dead time ignored','Dead time modeled'],['0.65','0.069','0.706']],[384,384,384],514,104,23);
 footer(s,'Other fitted parameters remained biased. Classical sequence models also use history. IBM used known models.');
 note(s,'The QRSM connects each bit to a hidden-state model','1:35–2:35',
 'The QRSM connects each observation to a physical hidden-state model. Each bit conditions the emitter and possible defect state, contributes to the record likelihood, and changes the next prediction. Across records, classical fitting compares coupling and noise settings. A fresh synthetic test shows why this matters. Ignoring detector dead time pushed inferred coupling from a true0.65to0.069. Modeling the blind detector bin moved it to0.706and improved prediction on unused records. Other parameters stayed biased. A detector error can otherwise receive a false physical explanation. Classical hidden-state models also capture history, so the quantum structure must earn its value. Our IBM experiment uses a prepared zero state and known model settings. Grover then queries that model; it does not identify an arbitrary unknown state.',
 'qrsm_grover/model.py kraus, record_log_probability and branches. Fresh inference: qrsm_photon_poc/followup/README.md and inference_results/fixed_411101_dead1_fit0.json, fixed_411101_dead1_fit1.json. Coupling rounded0.069 and0.706 versus truth0.65. Held-out log-score improvement0.4584nats/24-bin record, conditional95%interval0.3978–0.5210. Other parameters biased/boundary. Independent score review in followup/independent_review.json. Conditional trajectories are established prior work: Murch etal., Nature502211(2013), https://arxiv.org/abs/1305.7270.',
 'Nicholas explains the QRSM itself before any acceleration claim. Distinguish updating the state within a model from estimating the model parameters across many records.');
}

{
 const s=slide('Hidden memory changes what follows a click',5);
 txt(s,'Given a click at step 3, how likely is another click later?',64,134,1152,48,28,C.ink);
 txt(s,'Probability of a later click',64,197,780,35,23,C.muted);
 chart(s,'line',{position:{left:64,top:243,width:805,height:318},categories:['Step 4','Step 5','Step 6'],series:[
  {name:'No hidden defect',values:after.models.no_hidden_defect.exact_conditional_probabilities.map(v=>Number(v.toPrecision(12))),fill:C.ochre,line:{fill:C.ochre,width:3}},
  {name:'With hidden defect',values:after.models.with_hidden_defect.exact_conditional_probabilities.map(v=>Number(v.toPrecision(12))),fill:C.teal,line:{fill:C.teal,width:3}}],hasLegend:true,legend:{position:'bottom',textStyle:{fontSize:21,fill:C.ink}},chartFill:C.cream,plotAreaFill:C.cream,xAxis:{textStyle:{fontSize:23,fill:C.ink},line:{fill:C.line,width:.6}},yAxis:{min:0,max:.12,majorUnit:.04,numberFormatCode:'0%',textStyle:{fontSize:18,fill:C.muted},majorGridlines:{fill:C.line,width:.6}},dataLabels:{showValue:false}});
 txt(s,'At step 6',934,239,280,38,24,C.muted);
 txt(s,'10.10%',927,291,290,65,49,C.ochre,true);
 txt(s,'without hidden defect',931,357,280,40,20,C.muted);
 txt(s,'4.67%',927,430,290,65,49,C.teal,true);
 txt(s,'with hidden defect',931,496,280,40,20,C.muted);
 footer(s,'Exact predictions. The new IBM follow-up separates these programmed models in one circuit, with persistent bias.');
 note(s,'Hidden memory changes what follows a click','2:35–3:20',
 'This is the useful prediction. Given a click at step three, how likely is another later? Without a hidden defect, the click resets the modeled emitter. A coupled hidden qubit retains memory and changes what follows. At step six, these models predict about ten percent and five percent. History gives a richer test than an overall count. A new IBM follow-up separates the programmed alternatives in one circuit, but keeps substantial bias. Other implementations reverse the contrast. The exact curves explain what the query should return. More accepted shots must also preserve that answer.',
 'research-validation/original_after_click_verification.json. Direct reproduction of qrsm_grover/queries.py exact_after_click and results/e5_inside_loop/noiseless.json. Conditional probabilities given step3=1, not stationary optical g2. Coupling phi=.45,zeta=.3 versus no hidden defect, theta=.6,gamma=.2.',
 'The audience should understand the two curves before hearing how Grover obtains the samples.');
}

{
 const s=slide('Rare conditions waste ordinary samples',6);
 txt(s,pct(exactP,2),64,159,500,99,77,C.teal,true);
 txt(s,'of ideal runs have the selected click',68,266,580,42,27,C.ink);
 txt(s,'About 25 runs per matching sample',68,321,630,48,29,C.ink,true);
 txt(s,'Quantum query scaling',758,163,458,42,29,C.ink,true);
 txt(s,'1 / p',757,234,440,68,50,C.muted);
 txt(s,'ordinary rejection',758,307,440,37,25,C.muted);
 txt(s,'1 / √p',757,378,440,68,50,C.teal,true);
 txt(s,'ideal coherent model calls',758,451,450,38,25,C.ink);
 txt(s,'p = probability of the selected event',758,497,450,30,20,C.muted);
 txt(s,'Today, a classical conditional sampler\nwins this small problem',64,532,1152,84,31,C.ink,true);
 footer(s,'A possible benefit needs larger quantum memory and sufficiently accurate reversible circuits.');
 note(s,'Rare conditions waste ordinary samples','3:20–4:05',
 'The selected click occurs in3.95percent of ideal runs. Ordinary rejection needs about25runs for one match, with cost growing as one over its probability. Amplitude amplification reduces coherent model calls to order one over the square root of that probability. That is the quantum rationale, not a wall-clock speedup. Our strongest classical baseline directly samples conditional answers without rejection and wins at this small size. The possible future opportunity is a hidden quantum memory that becomes expensive to represent classically, provided the reversible quantum circuit stays accurate. That crossover remains unproven.',
 'ExactP from summary_plain.json. Classical backward sampler: docs/REPORT.md section5 and qrsm_grover/classical.py. Amplitude amplification https://arxiv.org/abs/quant-ph/0005055. Quantum inference precedent https://arxiv.org/abs/1402.7359. Cost includes calls to preparation and its inverse, with additional oracle/reflection gates.',
 'Dan explains the fair classical comparison and why this remains quantum-computing research.');
}

{
 const s=slide('A reversible model makes amplification possible',7);
 await img(s,root+'/rewindandamplify-main/results/figures/fig_circuit_grover.png',64,137,1152,350,'Preparation of histories, event oracle, inverse preparation and reflection');
 const lab=txt(s,'3 Reflect about the prepared state',566,164,445,34,21,'#AF451C',true);lab.fill='#FBFBFA';
 const rec=txt(s,'records |0…0⟩',135,373,136,38,18,C.ink);rec.fill='#FBFBFA';
 txt(s,'Save the history',64,515,278,39,25,C.ink,true);
 txt(s,'Fresh qubits\nreplace resets',64,558,278,60,22,C.muted);
 txt(s,'Steer the model',358,515,278,39,25,C.ink,true);
 txt(s,'Classical tuning\nof a supported event',358,558,278,60,22,C.muted);
 txt(s,'Amplify locally',652,515,278,39,25,C.teal,true);
 txt(s,'Fewer gates\nwith approximation',652,558,278,60,22,C.muted);
 txt(s,'Check the answer',946,515,278,39,25,C.ink,true);
 txt(s,'Event rate and\nconditional accuracy',946,558,278,60,22,C.muted);
 footer(s,'Qiskit circuit construction, Aer verification, IBM compilation and archived plus fresh device counts.');
 note(s,'A reversible model makes amplification possible','4:05–5:00',
 'Grover must run the model backward, but a reset discards information. We replace each reset with a fresh output qubit and defer measurement. A prepares the histories. The oracle marks the selected condition. A dagger reverses the preparation. A reflection followed by preparation changes interference so matching histories become more likely. We then reduce hardware cost. Steering is classical tuning of a supported event. Local reflection checks fewer qubits but introduces approximation. We verify both event rate and conditional accuracy. Qiskit builds the circuits, Aer checks the exact model, and compiled circuits run on IBM. Amplification is established. Our contribution is this recurrent-model construction and its tested adaptations.',
 'rewindandamplify-main/qrsm_grover/model.py, amplify.py, queries.py and tests. Steering helpers are in amplify.py. Original circuit figure fig_circuit_grover.png with corrected prepared-state terminology. Prior amplification and Bayesian-network inference: Brassard et al. and Low, Yoder, Chuang 2014. Before-event QRSM and during-event contributions documented in original README.',
 'Dan explains A and A dagger. Nicholas explains the implementation changes and verification. Technical model circuit is in backup.');
}

{
 const s=slide('Fewer gates, more matching answers',8,true);
 txt(s,'Fresh IBM Marrakesh follow-up. Same steering and initial qubit mapping.',64,134,1150,43,25,C.light);
 txt(s,'Raw matching-event rate',64,184,748,33,23,C.light);
 chart(s,'bar',{position:{left:62,top:215,width:748,height:320},categories:['Local reflection','Full reflection'],series:[{name:'Raw selected-event rate',values:[hwHero.first.probability,hwHero.second.probability],points:[{idx:0,fill:C.cyan},{idx:1,fill:C.amber}],valuesFormatCode:'0.00%'}],barOptions:{direction:'bar',grouping:'clustered',gapWidth:90},hasLegend:false,chartFill:C.navy,plotAreaFill:C.navy,xAxis:{textStyle:{fontSize:24,fill:C.cream},line:{fill:'none',width:0},majorGridlines:null},yAxis:{min:0,max:1,numberFormatCode:'0%',textStyle:{fontSize:18,fill:C.light},majorGridlines:{fill:C.slate,width:.6},line:{fill:'none',width:0}},dataLabels:{showValue:true,position:'outEnd',numberFormatCode:'0.00%',textStyle:{fontSize:28,fill:C.cream,bold:true}}});
 txt(s,'58 vs 125',908,221,310,72,50,C.cyan,true);
 txt(s,'native CZ gates\nlocal / full',912,301,300,66,23,C.cream);
 txt(s,'0.118 / 0.181',908,398,310,49,32,C.cream,true);
 txt(s,'raw conditional error*\nlocal / full',912,451,300,65,22,C.light);
 txt(s,'Useful computation needs both accepted samples and accurate answers',64,555,1150,60,27,C.cyan,true);
 footer(s,'8,192 shots each. *Conditional-history TV, lower is closer. Follow-up selected after the first run. Routing differs.',true);
 note(s,'Fewer gates, more matching answers','5:00–6:00',
 'We repeated the comparison on IBM Marrakesh with a common initial qubit mapping. In this fresh follow-up, local reflection returned76.90percent matching shots, versus69.26percent for full reflection. It used58rather than125native two-qubit gates. The gain is7.64percentage points, with a shot-based interval from6.29to8.99. Shorter circuits use fewer scarce operations per accepted answer here. Conditional error is also lower:0.118versus0.181, where zero is ideal. This still leaves bias. Routing and circuit widths differ, and the follow-up was selected after the first run. Suppression did not improve the earlier comparison. Reliable qubits and accurate circuits matter together. We claim this bounded cost-and-quality result, not dollar savings or a classical speedup.',
 'hardware_campaign/runs/original_precision_v1/analysis.json and hero_acceptance_contrast.json. Raw6300/8192 versus5674/8192. Same steering,r1, shared initial logical-to-physical map prefix. NativeCZ58/125, raw conditional-history TV versus unsteered ideal.1177208/.1813871. Independent stationary Bernoulli interval excludes drift, calibration, context and model error. First current run77.39/64.26% at2048shots, not pooled. Archived Kingston86.06/78.49% and40/85gates remain historical evidence. No universal causal or total-cost advantage.',
 'Dillon identifies this as the new precision follow-up. Separate raw quality, event yield and native operations. Backup14 preserves first run, suppression and historical context.');
}

{
 const s=slide('The query returns a prediction about the next clicks',9,true);
 const shot=root+'/laser-diagnostics-app/app-core-query.jpg';
 try{const b=await fs.readFile(shot);s.images.add({blob:b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength),contentType:'image/jpeg',alt:'Offline original QRSM demonstration with selected condition and conditional future probabilities',fit:'contain',crop:{left:.01,top:.18,right:.01,bottom:.03},position:{left:64,top:149,width:1152,height:447}});}
 catch(err){if(!draft)throw new Error('Reviewed app-core-query.jpg is required for final revision.');await img(s,root+'/rewindandamplify-main/results/figures/fig_after_click.png',64,149,1152,447,'Original conditional future probabilities on simulated devices');}
 footer(s,'Live local demonstration of the original model. Static screenshot remains available if switching fails.',true);
 note(s,'The query returns a prediction about the next clicks','6:00–6:45',
 'In the app, we select a click at step three. Switching from plain sampling to full amplification raises acceptance while preserving the predicted future probabilities. Now switch the hidden-memory model to an emitter alone. The step-six probability changes from about five percent to ten percent. That is the answer we wanted: how a candidate hidden interaction changes later observations. These are saved, verified model calculations. The separate IBM data measure circuits representing those models. Neither is a live laser measurement, and amplification does not increase photons from a real source.',
 'laser-diagnostics-app original-core section and research-validation/original_after_click_verification.json. Original source queries.py and e5_inside_loop/noiseless.json. This demonstration is distinct from the separate two-bin cavity model.',
 'Timofey demonstrates for 45 seconds: 0–8 explain the QRSM role, 8–15 define the selected click, 15–27 choose Steering + full, 27–38 switch to Emitter only, 38–45 explain the diagnosis boundary and return to slides. Pre-open Focus view and the original QRSM chapter. Do not troubleshoot during the talk.');
}

{
 const s=slide('Quantum-dot source quality and the QRSM',10,true);
 txt(s,'The original question: what hidden environment could explain the record?',64,134,1150,45,28,C.cream);
 txt(s,'The semiconductor task',64,223,570,50,31,C.cyan,true);
 txt(s,'Equal photon counts can hide\ndifferent interference quality.',64,301,570,121,30,C.cream);
 txt(s,'Engineers: qualify and tune\nsources for photonic chips.',64,467,570,80,27,C.light);
 txt(s,'Joint observation implemented',724,223,492,50,28,C.amber,true);
 txt(s,'A new dot + environment model\npredicts two-photon outcomes\nand updates hidden memory.',724,301,492,121,27,C.cream);
 txt(s,'Classical predictions checked.\nDigital circuits tested on IBM.',724,467,492,80,26,C.light);
 txt(s,'Photonic operations rely on predictable interference',64,565,1152,54,29,C.cyan,true);
 footer(s,'Hypothetical source model. No fit to a real dot or defect diagnosis. Laser-frequency monitoring is a separate experiment.',true);
 note(s,'Quantum-dot source quality and the QRSM','6:45–7:25',
 'Quantum dots connect our question to semiconductor photon sources. Photonic operations rely on predictable interference, which equal brightness cannot guarantee. Engineers need to qualify and tune sources for photonic chips. We now implement a joint-photon observation model: the hidden environment changes emitted modes, and each pair outcome updates its conditional state. Classical calculations verify it, and IBM circuits test its digital representation. The first small-data test barely distinguishes the hypotheses. More controlled data helps, but calibration errors can imitate the signal. No real dot is fitted. Next is our separate frequency-monitoring study.',
 'quantum_dot_bridge/qrsm_hom_followup/README.md, physical_model.py, circuits.py and main/results.json. New complete-emission dispersive surrogate, not the original QRSM excitation-exchange model. Complex temporal Gram embedding and controlled-SWAP parity represent HOM, checked independently with bosonic operators. Main64attempted-pair held-out flags5.60% coherent versus4.50% classical. Separate selected design uses ideal resets and calibrated source shifts; stronger HMM predictions tie within uncertainty. Hardware: hardware_campaign/runs/dots_plain_v1 and dots_suppressed_v1, plus selected-four-pair extension. No semiconductor source/laser measurement, fitted external GaAs trajectory or quantum-memory certification. Integration precedent: Davancoetal2017, https://www.nist.gov/publications/heterogeneous-integration-chip-quantum-photonic-circuits-single-quantum-dot-devices. HOM information context: https://arxiv.org/html/2203.08682v1. External histograms remain separately analyzed.',
 'Nicholas explains the implemented observation model and its limits. Keep the engineering task concrete: source qualification and tuning. Backups30–33 show why correlations, calibration and acquisition budget matter. Transition to the distinct atomic-frequency benchmark on11.');
}

{
 const s=slide('The classical reference leads with unknown onset',11);
 const n=sensorNow.scenarios.find(x=>x.id==='unseen_nominal_sessions');const keys=['classical','classical_quantum','two_classical'];
 txt(s,'Detection within 32 s of a ±0.5 Hz step. Its start time is hidden.',64,137,1150,42,26,C.muted);
 // Eight decimal fraction digits preserve displayed percentages while fitting Excel's numeric precision.
 chart(s,'bar',{position:{left:64,top:211,width:815,height:338},categories:['Conventional C','C + atomic Q','C + independent C'],series:[{name:'Detection within 32 seconds',values:keys.map(k=>Number(n.methods[k].detection_within_32s.toFixed(8))),points:[{idx:0,fill:'#8395A0'},{idx:1,fill:C.teal},{idx:2,fill:C.ochre}],valuesFormatCode:'0.00%'}],hasLegend:false,barOptions:{direction:'column',gapWidth:95},chartFill:C.cream,plotAreaFill:C.cream,xAxis:{textStyle:{fontSize:22,fill:C.ink},line:{fill:C.line,width:.6}},yAxis:{min:0,max:1.1,majorUnit:.25,numberFormatCode:'0%',textStyle:{fontSize:17,fill:C.muted},majorGridlines:{fill:C.line,width:.6}},dataLabels:{showValue:true,position:'outEnd',numberFormatCode:'0.00%',textStyle:{fontSize:28,fill:C.ink,bold:true}}});
 txt(s,'Atomic addition',923,235,292,42,25,C.muted);
 txt(s,'+6.67 points',923,295,292,65,37,C.teal,true);
 txt(s,'95% interval\n+3.96 to +9.38 points',923,379,292,80,24,C.muted);
 txt(s,'C + C still leads',923,492,292,51,27,C.ochre,true);
 txt(s,'Full-record false alarms: '+keys.map(k=>pct(n.methods[k].false_alarm_rate,2)).join(' / ')+'  (C / C + Q / C + C)',64,581,1150,38,21,C.muted);
 footer(s,'128 s records. 1,920 per class. Unseen sessions. Nominal 5% alarm target. Total apparatus costs differ.');
 note(s,'The classical reference leads with unknown onset','7:25–8:10',
 'The test hides when frequency changes and holds out simulated sessions. Can the monitor respond within32seconds? The conventional receiver detects51.35percent. Adding the atomic channel reaches58.02percent, a6.67point gain. A second independent conventional reference reaches97.97percent. False alarms below refer to the entire128second record, not each instant. We include missed events in the delay calculation. Degraded atomic coherence can reverse the benefit, and shared-path drift still mimics the source. These controls sharpen our conclusion: an atomic reference can add information in this model, but the conventional addition performs best. Apparatus resources are not fully matched.',
 'laser_sensor_viability/followup/main/results.json, unseen_nominal_sessions. Detection within32s C.5135416667,CQ.5802083333,CC.9796875. Full-recordFAR .0541666667,.0515625,.040625. Eight independent calibration pipelines,96held-out sessions,1920null and1920source records. Paired hierarchical bootstrap gain6.67pp[3.96,9.38]. Assumed698nm,64atoms,1scycle and975msdeadtime. Distinct task from the earlier known-midpoint benchmark.',
 'Dillon explains the unknown onset and32second horizon before the percentages. Do not quote the earlier86% known-time result here.');
}

{
 const s=slide('The evidence changes our next experiment',12);
 txt(s,'Drive-amplitude monitoring',64,164,580,47,32,C.ochre,true);
 txt(s,'3.71% timely detection',64,237,575,63,37,C.ink,true);
 txt(s,'6.84% false source alarms',64,310,575,45,26,C.muted);
 txt(s,'This budget gives\nno useful prompt warning',64,392,575,85,30,C.ink,true);
 txt(s,'Revise the operating point\nbefore a sensor prototype.',64,512,575,75,26,C.muted);
 txt(s,'Phase inspection model',724,164,492,47,32,C.teal,true);
 txt(s,'0.00637 vs 0.00791 rad',724,237,492,63,33,C.ink,true);
 txt(s,'Hybrid / coherent phase error',724,310,492,45,25,C.muted);
 txt(s,'A conditional precision benefit\nmerits a calibrated optical test',724,392,492,85,28,C.ink,true);
 txt(s,'20,000 incident photons\n81% overall efficiency',724,512,492,75,26,C.muted);
 footer(s,'Separate simulations. Drive: +20% field step, 32-bin detection horizon, 96-bin alarm record. No wafer result.');
 note(s,'The evidence changes our next experiment','8:10–8:50',
 'In simulation, a20percent drive step gives only3.71percent detections within32bins and6.84percent false alarms per96-bin stable record. Most amplitude-estimation gain comes from its prior, so this regime needs redesign. A separate phase simulation is promising: a charged hybrid reduces error from0.00791to0.00637radians at matched incident photons and ideal preparation. Loss and preparation time matter. Next, test a calibrated optical target with an independent reference. Computing also needs accurate answers at competitive total cost. Neither path has demonstrated a wafer benefit.',
 'RESEARCH_CURRENT.md; archived phase and drive studies summarized in RESEARCH_RESULTS.md. Drive: qrsm_photon_poc/drive_diagnostics_followup/main/results.json and prior_only_estimation_control.json, independent reviews. Phase: quantum_lithography_poc/phase_inspection_followup/results.json high_efficiency/equal_sample_photons/global.20,000mean photons before object, both modes charged,T=.9,D=.9,p=1,10%coherent/90%NOON. RMSE hybrid.00637086 versus coherent.007908rad. Global phase prior over2pi, assumed known phase reference. No fabricated sample or industrial process test.',
 'Nicholas states the negative amplitude result and the conditional phase opportunity. Save prior-control and ambiguity details for backups25–26.');
}

{
 const s=slide('Our contribution and what we learned',13,true);
 txt(s,'A queryable recurrent quantum model',64,151,1150,50,36,C.cyan,true);
 txt(s,'Reversible construction and hardware adaptations,\nwith independent checks and fresh IBM experiments',64,217,1150,88,29,C.cream);
 txt(s,'Controls changed our conclusions. Accuracy and total cost both matter.',64,337,1150,62,29,C.cream,true);
 txt(s,'Nicholas Taylor',64,445,535,33,24,C.cyan,true);txt(s,'QRSM research, Grover fusion, experiments',64,482,535,46,20,C.light);
 txt(s,'Timofey Yudintsev',725,445,491,33,24,C.cyan,true);txt(s,'Research, keyword-search idea',725,482,491,46,20,C.light);
 txt(s,'Dan Izquierdo',64,548,535,33,24,C.cyan,true);txt(s,'Experimentation',64,586,535,37,20,C.light);
 txt(s,'Dillon Satria Sitepu',725,548,491,33,24,C.cyan,true);txt(s,'Formatting and revising',725,586,491,37,20,C.light);
 footer(s,'QRSM model predates the event. Known amplification methods. AI assistance: Claude and Codex / OpenAI.',true);
 note(s,'Our contribution and what we learned','8:50–9:20',
 'Our contribution is a queryable recurrent quantum model with fresh hardware tests and a joint-photon observation extension. Controls changed our conclusions: accuracy and cost both matter. Our documented team roles are here. The QRSM predates the event, and amplification is established. We used Claude originally and Codex with OpenAI models for the extensions. These results show what the computing method achieves and what optical experiments still need to test. Thank you.',
 'Original README sections PriorworkandAIhelp and Team. User confirmed the documented roles. New finals assistance includes research reconstruction, simulation implementation, tests, source review, app and presentation authoring. Prior amplification Brassardetal2000 and quantum inference Lowetal2014. Project repository https://github.com/Nicholas55555/rewindandamplify.',
 'Nicholas closes. Slides 14 onward are Q&A only. The planned 9:20 finish leaves 40 seconds for handoffs or pauses. Rehearse to confirm the actual time.');
}

async function addBackups(){
// Backup11: archived hardware counts and the independently repeated comparison.
{
 const s=slide('Hardware repeats and noise controls',14);
 const ids=['click3-steered-memory+last-1-r1','click3-steered-full-r1'];
 const vals=[['Current run','Shots each','Local raw','Full raw','Conditional TV*'],...[[hwFirst,'First plain'],[hwSuppressed,'Suppressed'],[hwPrecision,'Precision follow-up']].map(([run,label])=>{const a=ids.map(id=>run.rows.find(x=>x.name===id));return[label,String(a[0].shots),pct(a[0].observables.selected.probability,2),pct(a[1].observables.selected.probability,2),a.map(r=>r.observables.selected_history_tv_to_unsteered_target.toFixed(3)).join(' / ')];})];
 table(s,vals,[360,150,200,200,242],197,289,23);
 txt(s,'58 / 125 native CZ gates, local / full, in every current run',64,520,1152,48,29,C.teal,true);
 txt(s,'The follow-up confirms higher yield, with a different effect size',64,577,1152,42,27,C.ink,true);
 footer(s,'*Raw conditional-history TV, local / full. Lower is closer. Same initial map prefix; widths, routing and times differ.');
 note(s,'Hardware repeats and noise controls','Backup',
 'The three current runs remain separate. Suppression used dynamical decoupling and twirling; it did not improve this pair in the observed run. The larger-shot follow-up was chosen after inspecting the first campaign and must not be described as a preselected independent confirmation of all hypotheses. Its7.64point yield difference has an independent-shot interval6.29to8.99points, excluding drift and calibration uncertainty. First-run ablations also include plain6.74percent, steering-only24.07percent and unsteered full three-round48.73percent. Conditional accuracy differs strongly. Earlier Kingston results86.06/78.49percent and40/85gates remain historical, with different layouts. None are pooled or interpreted as a universal noise advantage.',
 'hardware_campaign/runs/original_plain_v2/analysis.json, original_suppressed_v1/analysis.json, original_precision_v1/analysis.json and hero_acceptance_contrast.json. All original43rows include the full earlier39circuit suite plus catalog repeats. Archived evidence research-validation/hardware_verification.json. Raw summaries primary; projected independent assignment inversion is a sensitivity analysis without calibration uncertainty.');
}
// Backup12: which approximation and which accuracy statement.
{
 const s=slide('Deep optical queries show large distribution errors',15);
 txt(s,'Three retained optical bins, all-click query, one amplification round on IBM',64,135,1152,52,27,C.muted);
 const ids=['optical_3bin_0p03_all_r1','optical_3bin_0p003_all_r1'];
 table(s,[['Choi cutoff','Qubits','Native CZ','Raw accepted','Data Z error*'],...ids.map((id,i)=>{let r=hwOptical.rows.find(x=>x.name===id);return[i===0?'0.03':'0.003',String(r.logical_qubits),r.native_two_qubit_gate_count.toLocaleString('en-US'),`${r.observables.accepted_shots} / ${r.shots}`,r.observables.data_z_distribution_tv.toFixed(3)];})],[210,150,270,280,242],211,218,25);
 txt(s,'Ideal acceptance is only about 0.128%',64,465,1152,50,31,C.teal,true);
 txt(s,'Zero hits alone is inconclusive at 512 shots. Distribution bias is substantial.',64,546,1152,65,27,C.ink,true);
 footer(s,'*TV of measured data-register Z probabilities versus the declared circuit target. No optical sensor or full-state fidelity.');
 note(s,'Deep optical queries show large distribution errors','Backup',
 'Both retained three-bin models pass exact branch and conditional-state checks before hardware. Native routing raises these queries to26,749and54,998CZgates. Each returns zero selected shots out of512. That alone is inconclusive: even ideal expected counts are below one. The measured data marginals have substantial total-variation error, while full data-plus-environment distributions deviate still more. The one-bin circuits can instead produce inflated acceptance with wrong conditional distributions. Better mathematical truncation therefore does not guarantee a more useful hardware answer. Classical recursion already solves these small models efficiently. Cavity-two is a deliberately truncated physical surrogate, and Z statistics do not establish full conditional-state fidelity.',
 'hardware_campaign/runs/optical_dilation_plain_v2/analysis.json and raw.json, rows optical_3bin_0p03_all_r1 and optical_3bin_0p003_all_r1. Raw0/512, Wilson upper.7447%, versus ideal.127833/.127551%. DataZTV.436846/.384204. Underlying genericCX10,189/19,864 from multibin_followup/main/ideal_0p03.json and ideal_0p003.json. State approximation error versus cavity2 .02604/.01094 before hardware is a different quantity.');
}
// Sensor technical backups use the frozen experiment output directly.
{
 const s=slide('Sensor assumptions and resource accounting',16);
 if(evidence){const c=evidence.config;
 table(s,[['Model element','Assumed setting'],['Compatible laboratory wavelength',`${c.wavelength_nm} nm, narrow-line optical drive`],['Atomic ensemble',`${c.atoms} independent, unentangled atoms`],['Interrogation',`${c.pulse_s*1000} ms pulse + ${c.dark_s*1000} ms dark time + ${c.pulse_s*1000} ms pulse`],['Record and acquisition gap',`${c.cycles} s record, ${evidence.resource_ledger.dead_time_s*1000} ms dead time per cycle`],['Relaxation and readout',`T₂ = ${c.t2_s*1000} ms, T₁ = ${c.t1_s} s; 2% / 4% readout errors`]],[435,717],163,363,24);
 txt(s,'Time and task match. Total apparatus resources do not.',64,556,1140,57,30,C.ochre,true);
 footer(s,'Photon allocation is assumed bookkeeping. Reference lasers, cooling, trapping and readout costs remain uncounted.');
 note(s,'Sensor assumptions and resource accounting','Backup',
 'The atomic response follows finite driven Bloch rotations with T1/T2 damping, preparation error, asymmetric readout error and binomial projection noise. Optical intensity changes the Rabi frequency and induces an assumed light shift during pulses. Conventional receivers include source-photon shot noise, electronics and reference drift. All methods see the same underlying source task and duration. The photon allocation is a declared assumption: atomic coupling and beam geometry are not specified from a real apparatus, and reference lasers plus atomic support optics are not included in a full cost comparison. Therefore this is not a resource-matched quantum advantage test.',
 'laser_sensor_viability/results.json config and resource_ledger supply the unchanged physical model. New task: followup/README.md, protocol.json and main/results.json. Unknown source onset48–96s, eight independently trained/calibrated pipelines, held-out sessions. Whole-record alarm calibration, misses and prealarms charged32sin restricted delay. Bishof etal., PRL111093604, https://arxiv.org/abs/1303.6741 is physical precedent, not chosen device specifications.');}
}
{
 const s=slide('Calibration failures can reverse the conclusion',17);
 if(sensorNow){const ids=['unseen_nominal_sessions','unseen_short_coherence','primary_reference_changes','common_sampled_path_changes'];const names=['Unseen nominal sessions','Shorter atomic coherence','Primary-reference step','Shared-path step'];
 const vals=[['Scenario','C detection / false alarm','C + Q','C + C'],...ids.map((id,i)=>{let r=sensorNow.scenarios.find(x=>x.id===id);return[names[i],...['classical','classical_quantum','two_classical'].map(k=>`${(100*r.methods[k].detection_within_32s).toFixed(1)}% / ${(100*r.methods[k].false_alarm_rate).toFixed(1)}%`)];})];
 table(s,vals,[375,315,231,231],176,345,23);
 txt(s,'Shared-path drift is indistinguishable from source drift here',64,552,1145,61,28,C.ochre,true);
 footer(s,'Each cell: detection within 32 s / false alarms per 128 s record. 1,920 null and source records per scenario.');
 note(s,'Calibration failures can reverse the conclusion','Backup',
 'These are the new unknown-onset results. Each cell gives timely detection followed by full-record false alarms. The target is source-frequency change, so a sensor/reference/path change can trigger a false source diagnosis. Shorter atomic coherence makes the fused channel worse than C alone. A separate agreement veto reduces the primary-reference failure but sacrifices sensitivity and still exceeds the nominal alarm target. Shared-path drift is structurally indistinguishable from source motion in this measurement model. Hierarchical pipeline/session intervals quantify finite simulation variation, not physical model error or calibrated universal coverage. None of the older known-midpoint rates belong in this table.',
 'laser_sensor_viability/followup/main/results.json and README.md. New primary-reference CQFAR84.53%, common-path94.11%. Agreement rule15.57% and68.23%, respectively. Nominal CQgain6.67pp, shortcoherence−5.42pp. Eight pipelines and96test sessions per scenario.');}
}
// Fresh synthetic joint inference: readout dynamics can be misattributed to coupling.
{
 const s=slide('Detector dead time can distort inferred coupling',18);
 txt(s,'Fresh synthetic records. True coupling = 0.65. Same data for both fits.',64,136,1152,48,27,C.muted);
 table(s,[['Physical model','Fitted coupling','Held-out score relative to HMM*'],['Dead time ignored','0.069','−0.4506 nats / record'],['Blind-bin dynamics included','0.706','+0.0078 nats / record']],[430,250,472],216,223,25);
 txt(s,'Modeling dead time improves prediction by 0.4584 nats / record',64,475,1152,63,29,C.teal,true);
 txt(s,'Corrected parameters still show bias and a dephasing boundary',64,558,1152,51,27,C.ochre,true);
 footer(s,'*24-bin records. Corrected model versus HMM interval spans zero. Synthetic inference, not physical defect diagnosis.');
 note(s,'Detector dead time can distort inferred coupling','Backup',
 'After a click, the next recorded bit is forced to zero while the underlying system evolves unconditionally. Ignoring that readout process misattributes detector correlation to the hidden interaction. Including it improves held-out log likelihood by0.4584nats per24-bin record, with paired conditional95%interval0.3978–0.5210. The fitted coupling moves closer to the known synthetic value, but dephasing reaches its upper bound and efficiency remains biased. A trained HMM captures the detector correlation too: the corrected physical model’s advantage over it is unresolved. Other physical parameters and the family remain known. This fresh result replaces the earlier truth-informed candidate-count example in the current deck.',
 'qrsm_photon_poc/followup/README.md, inference_results/fixed_411101_dead1_fit0.json, fixed_411101_dead1_fit1.json, parameter_validation_v2/ and independent_review.json. The HMM difference interval for the corrected model is−.0067to+.0222nats/record.');
}

// Backup16: separate physical sensing, inference and computational query claims.
{
 const s=slide('Where the quantum component enters',19);
 table(s,[['Layer','What it does','Evidence today'],['Sensor dynamics','Atomic response to modeled laser drive','Bloch model + digital IBM channel'],['Diagnostic inference','Combines acquisition records','Classical synthetic benchmark'],['Rare-history query','Amplifies a condition in a coherent model','Qiskit + actual IBM circuits']],[300,460,392],190,330,25);
 txt(s,'A sensing benefit does not establish a computing speedup',64,565,1152,51,30,C.teal,true);
 footer(s,'Individual channels ran digitally. The full acquisition and diagnostic benchmark remains a separate simulation.');
 note(s,'Where the quantum component enters','Backup',
 'A sensor can use quantum dynamics while a classical computer processes its readouts. We now compile the finite driven atomic channel, including dissipation, into an IBM digital circuit. That tests a bounded implementation on superconducting hardware, not an atom, physical optical coupling or a128second acquisition. Unknown-onset detection still runs as classical inference on synthetic records. The separate recurrent-model query uses coherent preparation and amplitude amplification. Connecting a calibrated full acquisition process to a competitive quantum algorithm remains further work. No end-to-end quantum advantage follows from executing a component.',
 'hardware_campaign/optical_controls/README.md, models.py and hardware_integration_review.json. Canonical laser_sensor_viability/model.py. Independent Bloch versus Lindblad/Stinespring checks. LASER_DIAGNOSTICS_ROADMAP.md and hardware_campaign/coverage.json distinguish component, classical and physical requirements.');
}
// Backup17: actual lithography source differences and the appropriate experiment.
{
 const s=slide('The transfer to lithography needs its own test',20);
 table(s,[['Signal','Physical role','Current model'],['193 nm excimer light','DUV exposure source','Not represented'],['CO₂ drive laser','Creates a tin plasma for EUV','Not represented'],['13.5 nm EUV','Plasma emission used for exposure','Not represented'],['698 nm laboratory laser','Compatible narrow-line atomic probe','Synthetic surrogate']],[360,470,322],169,345,24);
 txt(s,'Conventional source diagnostics already exist',64,547,1140,44,30,C.teal,true);
 footer(s,'Proposed value: test complementary information on synchronized observations, then assess a specific source.');
 note(s,'The transfer to lithography needs its own test','Backup',
 'The distinction matters. A CO2drive laser heats tin to create plasma, which emits EUV. Monitoring the drive is different from measuring EUV. A narrow-line698nm atomic benchmark does not automatically transfer to either of those signals or to a193nm broadband pulsed excimer source. Existing conventional monitoring measures relevant source quantities. Cymer and imec reported controlled wafer experiments correlating light-source changes with critical-dimension behavior. That motivates source metrology, not a quantitative yield claim for our sensor. Atomic laser-noise metrology is also established prior work, including Bishof and colleagues in2013.',
 'ASML: https://www.asml.com/en/technology/lithography-principles/light-and-lasers and https://www.asml.com/en/products/euv-lithography-systems. Cymer/imec2014: https://www.cymer.com/wp-content/uploads/2018/12/Cymer_SPIE_AdvancedLithography_2014.pdf. Bishof etal.: https://arxiv.org/abs/1303.6741.');
}
}
await addBackups();
{
 const s=slide('The continued query separates models with bias',21);
 const ids=['plain','steered_local','steered_full','steered_memory'];
 const labels=['Plain','Steer + local','Steer + full','Memory-only control'];
 table(s,[['Circuit','Defect: step 6*','No defect: step 6*','Difference, points'],...ids.map((id,i)=>{const r=hwLoops.comparisons[id].find(x=>x.step===6);return[labels[i],pct(r.first.probability,2),pct(r.second.probability,2),(100*r.probability_difference).toFixed(2)];})],[380,270,280,222],181,330,24);
 txt(s,'Exact: 4.67% / 10.10%. Local follow-up difference: −2.87 points.',64,543,1152,48,27,C.teal,true);
 footer(s,'*Raw rate given step-3 click. 8,192 shots before conditioning. Local difference 95% shot interval: −3.89 to −1.84 points.');
 note(s,'The continued query separates models with bias','Backup',
 'The selected precision follow-up uses8192shots per circuit. Its steered local implementation gives step-six rates8.794percent with the programmed defect and11.661percent without it. The raw contrast has the intended sign and a shot-based interval excluding zero. Both rates remain biased relative to4.667and10.102percent exact targets. Crucially, plain, steered full and memory-only implementations reverse the expected sign. The initial campaign also failed to resolve the small local contrast at its lower precision. We preserve these results rather than calling this reliable diagnosis. The effect distinguishes particular programmed circuits under particular conditions; it does not locate unknown defects in the IBM processor or a laser.',
 'hardware_campaign/runs/original_precision_v1/loop_contrasts.json and analysis.json. Local step6counts538/6118 versus834/7152 accepted histories. Contrast−.0286735, independent-shot Wilson-based95%interval[−.0389321,−.0183558]. Intervals exclude drift, readout-calibration and model uncertainty. Original ideal target research-validation/original_after_click_verification.json. Earlier archived continued jobs remain separate historical evidence.');
}
{
 const s=slide('One step of the recurrent quantum model',22);
 await img(s,root+'/rewindandamplify-main/results/figures/fig_circuit_hybrid.png',64,148,1152,395,'Original emitter, hidden defect and output-qubit model circuit');
 txt(s,'Dynamic version: measure and reset the output',64,556,1152,48,29,C.teal,true);
 footer(s,'Purified version retains a fresh output for each step and defers measurement, preserving the click statistics.');
 note(s,'One step of the recurrent quantum model','Backup',
 'The emitter rotates under a drive. A hidden qubit rotates under its detuning and exchanges excitation with the emitter. The emitter then exchanges with a fresh output qubit. The dynamic implementation measures and resets that output each step. The purified implementation retains it, so the environment and history required for reversal remain in the circuit. This trades extra qubits for reversibility. Model steps are dimensionless. The optical labels describe a model interpretation. These IBM circuits did not measure photon arrivals.',
 'Original fig_circuit_hybrid.png, qrsm_grover/model.py and tests. QRSM defaults theta=.6,gamma=.2,phi=(.45,),zeta=(.3,).');
}
{
 const s=slide('Judging rubric and evidence map',23);
 table(s,[['Criterion','Weight','Where the talk addresses it'],['Problem and impact','15%','1–5, 8, 10, 12: purpose, measurement, cost'],['Quantum rationale','20%','4, 6–7, 15, 27, 32: model and limits'],['Technical Qiskit implementation','20%','7–9, 14–15, 21–22, 32–35: circuits'],['Results and evaluation','10%','4–5, 8, 11–12, 14–18, 25–35'],['Innovation','10%','7, 13, 24, 32: contribution and prior work'],['Presentation','15%','13 main slides, planned 9:20 including demo'],['Q&A and teamwork','10%','13–35: roles, lessons, evidence backups']],[380,135,637],150,458,22);
 footer(s,'Hardware bonus: highest applicable tier, up to +5. Evidence supports evaluation, not a guaranteed score.');
 note(s,'Judging rubric and evidence map','Backup',
 'This map follows the supplied Qiskit Fall Fest judging rubric. Exceptional performance asks for a specific stakeholder and realistic impact, a defensible quantum rationale that considers classical alternatives and hardware scale, reproducible Qiskit implementation, rigorous comparisons, a clear contribution relative to reused ideas, accessible delivery within the time limit, and shared understanding. The hardware bonus is a separate highest-tier item, not an additive sum of all tier values. We do not predict a judge score.',
 'User-supplied Qiskit_Fall_Fest_Judging_Rubric.xlsx, extracted by root. FINALS_RUBRIC.md.');
}
{
 const s=slide('Contribution, prior work and AI assistance',24);
 table(s,[['Origin','What belongs there'],['Established prior work','Amplitude amplification and amplified conditional inference'],['Before the event','QRSM idea, physics-shaped model and exact filter'],['Original hackathon work','Qiskit realization, Grover fusion, steering, local reflection, experiments'],['Finals extension','Independent model audits, joint-photon model and fresh hardware campaign'],['AI assistance','Original: Claude. Finals: Codex with OpenAI models']],[370,782],164,390,23);
 txt(s,'A sensing benefit and a computing speedup are separate claims',64,574,1150,47,28,C.teal,true);
 footer(s,'Atomic laser-noise spectroscopy also predates this project. No new atomic sensing principle is claimed.');
 note(s,'Contribution, prior work and AI assistance','Backup',
 'The original README documents the team research timeline and Claude assistance. The team set the original direction and questions and reviewed the work. This finals revision uses Codex and OpenAI models to assist research review, reproduction, simulations, tests, application and presentation. Do not imply that every generated analysis has already received manual team verification. Amplitude amplification and Bayesian quantum inference are prior art. Atomic laser-noise spectroscopy is also prior art. The separate optical and sensing extensions test scoped feasibility questions and do not establish an end-to-end quantum computing advantage.',
 'Original README PriorworkandAIhelp and Team. Brassardetal https://arxiv.org/abs/quant-ph/0005055. Lowetal https://arxiv.org/abs/1402.7359. Bishofetal https://arxiv.org/abs/1303.6741.');
}

{
 const s=slide('Drive amplitude: a useful negative result',25);
 txt(s,'Same 96-bin records. Unknown +20% field step. Detection within 32 bins.',64,135,1152,53,26,C.muted);
 table(s,[['Detector','Timely detection','Stable-record false alarms'],['Physical QRSM','3.71%','6.84%'],['Classical HMM','3.13%','5.27%'],['Count baseline','1.76%','1.95%']],[430,350,372],204,250,25);
 txt(s,'Prior-only RMSE 0.1136 → observed-data RMSE 0.1125',64,482,1152,55,30,C.teal,true);
 txt(s,'Most of the apparent estimation gain came from the prior',64,552,1152,51,28,C.ochre,true);
 footer(s,'Post-holdout prior control is descriptive. 512 records per case; 6,656 total. No physical time or photon-budget calibration.');
 note(s,'Drive amplitude: a useful negative result','Backup',
 'The field-amplitude proxy is the drive parameter, not an incident-photon flux. A20percent field step would correspond to44percent intensity under fixed coupling. This low-count regime yields poor timely detection alongside substantial full-record false alarms. The physical filter, fitted HMM and count detector share the same bits; these are not independent engineered optical receivers. The post-holdout prior-only control exposes a weak constant-estimate comparison: for this step, using observations only slightly improves the prior estimate, and for the four other source-changing cases it makes estimation worse. Afterpulsing produces10.55percent false source alarms. The model needs a better operating regime and calibrated detector dynamics before a practical monitor claim.',
 'qrsm_photon_poc/drive_diagnostics_followup/README.md; main/results.json, prior_only_estimation_control.json, independent_review.json, prior_only_independent_review.json. Four separately calibrated pipelines,13cases,128records per pipeline/case,96bins/cavity4. Stable FAR35/512 and step timely19/512 for physical QRSM. Prior-only MSE minus observed-data MSE .00025149, paired interval [.00007878,.00044596] for this step, a small conditional effect. Prior supplement is post-holdout descriptive, not another confirmatory test.');
}
{
 const s=slide('Phase inspection: benefit depends on the budget',26);
 txt(s,'Two illuminated sample modes. All incident photons are charged before loss.',64,135,1152,53,26,C.muted);
 table(s,[['Protocol at 81% efficiency','Full 2π phase RMSE','Wrong π branch'],['Coherent reference','0.00791 rad','0 / 2,000 trials'],['Pure two-photon NOON','2.22674 rad','50.4%'],['10% coherent + 90% NOON','0.00637 rad','0 / 2,000 trials']],[530,360,262],208,253,24);
 txt(s,'20,000 mean incident photons; ideal preparation in this comparison',64,491,1152,48,27,C.teal,true);
 txt(s,'1% preparation: matched dose takes 100× longer for pure NOON',64,558,1152,51,27,C.ochre,true);
 footer(s,'Synthetic phase task, known reference and loss. Hybrid pilots are charged. Zero observed branch errors is not a guarantee.');
 note(s,'Phase inspection: benefit depends on the budget','Backup',
 'A doubled fringe has a pi ambiguity. Pure NOON performs well locally around a shared calibrated working point, but fails to identify the full phase globally. A charged coherent pilot resolves that ambiguity in the tested hybrid. Both sample modes illuminate the object; the resource is20,000mean photons before object transmission, including reference-arm photons. The high-efficiency case has90percent object transmission and90percent detection, with ideal preparation. Lower transmission removes the precision benefit. At one-percent preparation, matching dose requires100times longer for pure NOON; at fixed clock time its precision is worse. Ideal number-resolving detection, a known phase reference and the declared classical protocol bound this result. It is not superiority over all classical designs or a measured feature-size benefit.',
 'quantum_lithography_poc/phase_inspection_followup/README.md and results.json high_efficiency/equal_sample_photons. Pure NOON modulo-pi RMSE .0062646rad, full2piRMSE2.226739rad. Hybrid.00637086rad, coherent.007908rad,2000outcomes per protocol in each cohort. Zero errors gives95%Wilson upper bound.1917%. Global phases reused across methods; outcomes independently drawn. Separate equal-clock and equal-dose budgets.');
}
{
 const s=slide('The full spatial query is costly to construct',27);
 txt(s,'49 exposure cells, capped photon counts and a reversible weighted threshold',64,135,1152,54,27,C.muted);
 table(s,[['Constructed bound','Qubits','Generic CX upper bound','Dose-1.5 event probability'],['Floor weights','389','3,382,108','0.00423713'],['Ceiling weights','389','2,874,028','0.00422695']],[300,170,332,350],218,218,24);
 txt(s,'196 count qubits + 23 score qubits + 170 extra clean ancillas',64,471,1152,56,28,C.teal,true);
 txt(s,'Both circuit files round-trip. Classical evaluation is already tractable.',64,553,1152,57,28,C.ink,true);
 footer(s,'389 qubits exceed the available 156-qubit device. Unoptimized bounds; no full-state simulation or physical optical claim.');
 note(s,'The full spatial query is costly to construct','Backup',
 'This is an actual constructed reversible49-cell oracle, not an extrapolation from three cells. Four count qubits per cell encode a capped Poisson law,23bits accumulate the weighted score, and170extra clean ancillas support explicit reversible gates. Both389qubit circuits pass QPY serialization and independent structural, arithmetic and uncomputation checks. The CX values are constructive generic decomposition upper bounds, including preparation and one complete amplification round; they are not a routed device compilation. Rounding and capped-tail bounds bracket the original event, with relative bracket width0.2406percent at dose1.5and0.3526percent at dose1.8. Classical dynamic programming already solves this independent-cell distribution efficiently. Construction alone establishes neither computational advantage nor physical lithography feasibility.',
 'finals-lithography/full_spatial_circuit/README.md, results.json, process_bounds.py, independent_review.json. Floor and ceiling clean circuits389qubits; CX bounds3,382,108/2,874,028 and U5,050,537/4,288,741. Dose1.5 original event bracket [.004226948015,.004237128599]; conservative conditionalTVbound.00482. Cap15 value change usesPoisson tailN>=16, encoded cap probabilityusesN>=15. Check row direction against event interval: floor weights admit an upper event; ceiling weights give a lower event.');
}
{
 const s=slide('Exposure: contrast trades against dose and loss',28);
 txt(s,'Phenomenological two-photon resist; fixed threshold and 20 evaluated guard cells',64,135,1152,53,26,C.muted);
 table(s,[['Illumination','Best mean cell accuracy','Incident photons','All 20 cells correct'],['Two-photon NOON','95.16%','14.88 million','36.76%'],['Phase-cycled coherent','78.28%','6.81 million','0.73%'],['10% duty coherent','83.29%','0.845 million','2.52%']],[360,300,250,242],209,254,24);
 txt(s,'Quantum contrast helps this chosen response; it is not dose advantage',64,491,1152,54,28,C.teal,true);
 txt(s,'Loss, blur and linear background can erase the pattern benefit',64,557,1152,53,29,C.ochre,true);
 footer(s,'Each row uses its own best tested dose. All phase-cycle exposures charged. Higher classical peak intensity is allowed.');
 note(s,'Exposure: contrast trades against dose and loss','Backup',
 'The response combines declared linear and two-photon activation coefficients, loss, phase jitter, finite pixel collection and post-activation blur. Activations are rare Poisson events, not direct photon probabilities. The NOON pattern has stronger mean contrast and higher best guard-cell accuracy under the nominal assumptions, but requires more incident photons at its best tested dose. The duty-cycle comparator concentrates equal average photons into ten-percent active time, giving higher peak intensity. It is one explicit classical competitor, not an optimum over all illumination. Loss, blur, linear leakage, background and low preparation success degrade the result. The20guard cells exclude boundary cells. This is a sensitivity study of an assumed resist, not a prediction for an available material or fabricated feature.',
 'quantum_lithography_poc/exposure_followup/README.md and results.json finite_nominal. Table optimizes each method over tested doses, so it is not a single equal-dose operating point. G1/G2 supplement verifies spatial conservation and harmonic/per-photon accounting. 540,000Poisson realizations. Wavelength800nm, ±30degree modes, second harmonic400nm; period is not linewidth. Independent or fast phase jitter/mean-rate approximation excludes slow correlated phase drift.');
}
{
 const s=slide('Model accuracy is part of the resource budget',29);
 txt(s,'Cavity truncation changes conditional predictions, even with exact circuit execution',64,135,1152,57,26,C.muted);
 table(s,[['Cavity levels','Default drive error*','Higher-drive error*'],['2','2.7643 percentage points','7.0829 percentage points'],['4','0.0494 percentage points','0.1118 percentage points'],['5','0.00281 percentage points','0.01102 percentage points']],[270,441,441],207,250,25);
 txt(s,'Controlled records improve some model comparisons; ambiguity remains',64,487,1152,61,29,C.teal,true);
 txt(s,'Classical filtering remains the baseline. More physics costs more qubits.',64,558,1152,51,28,C.ink,true);
 footer(s,'*Largest tested after-click probability error versus cavity level 6. Finite truncation study, not universal convergence.');
 note(s,'Model accuracy is part of the resource budget','Backup',
 'The original optical circuit uses only two cavity levels. Comparing its conditional predictions with a six-level reference reveals errors of several percentage points, especially under stronger drive. Increasing the cutoff reduces the discrepancy in these cases, but raises state and circuit costs. Six fresh joint-inference cases fit five parameters with source and detector controls. Fixed settings do not resolve performance versus an HMM; controlled settings give small held-out gains under shared known physics. Fixed-drive detuning sign remains structurally ambiguous. Controlled settings break that exact symmetry but do not establish reliable finite-data sign identification. Local curvature intervals fail near boundaries and are not global uncertainty guarantees. Thermal, multimode and non-Markovian effects remain future model families.',
 'qrsm_photon_poc/followup/README.md, dynamics_results.json, inference_results/, parameter_validation_v2/ and independent_review.json. Max after-click error over tested later lags versus cavity dimension6. Master equation independently checked with QuTiP; trajectory statistics tested separately. Controlled model-HMM logscore gains .0574[.0158,.1014] and .0972[.0448,.1495]nats/24-binrecord under conditional bootstrap. This does not establish physical defect identification or a quantum computational speedup.');
}

{
 const s=slide('Equal photon counts can hide poor interference',30);
 txt(s,'Same brightness and one-photon frequency distribution. Different pair correlations.',64,135,1152,53,26,C.muted);
 const memory=dotBridge.classical_trap_pair_comparison.filter(r=>[0,.5].includes(r.switch_probability_between_endpoints));
 table(s,[['Frequency relation in a pair','Each photon’s offset','Overlap M','Coincidence per attempt'],...memory.map((r,i)=>[i===0?'Shared offset':'Independent offsets','50% at either offset',r.conditional_overlap.toFixed(2),pct(r.coincidence_probability_per_excitation_pair,1)])],[350,300,170,332],209,238,24);
 txt(s,'A joint observation model now tests this broader memory question',64,479,1152,61,28,C.teal,true);
 txt(s,'80% versus 20% survival: 16× as many attempts per pair at lower efficiency',64,554,1152,51,26,C.ink,true);
 footer(s,'Attempt = two excitations. Classical environment, ideal preparation, 20% survival. M = 1 is ideal overlap. No quantum-memory advantage.');
 note(s,'Equal photon counts can hide poor interference','Backup',
 'Each photon separately has the same brightness and fifty-fifty frequency distribution. Shared versus independent offsets still change pair overlap from one to0.6. A single-photon marginal misses information in the joint observation. This benchmark environment is entirely classical, and an HMM is a necessary competitor. The new sequential HOM instrument implements the broader hidden-state question using a different complete-emission source model. Its digital circuits also test these frozen pair controls. It does not turn this classical memory example into a coherent-defect witness. An engineer can use the distinction to select interference-sensitive source measurements alongside collection cost. At80percent survival, a pair takes1.5625attempts on average; at20percent, it takes25. These are surviving pairs, not necessarily resolved coincidences.',
 'quantum_dot_bridge/results.json classical_trap_pair_comparison endpoints p_switch=0 and.5, PROTOCOL.md and independent_review.json. Both marginals are(.5,.5), ideal g2(0)=0 and eta=.2. M1/.6 gives coincidence per attempted excitation pair0/.008 at a balanced beamsplitter. The classical state remains fixed within each wavepacket; the pair model does not infer a switching time. Other benchmark cases retain counts while giving overlap1/.5/.2/.25 from pure dephasing or detuning. Sixteen tests and independent density-kernel quadrature support the calculations. External GaAs histograms are separate and did not calibrate this illustrative model. No semiconductor defect, physical device setting, quantum advantage or lithography yield was identified.');
}

{
 const s=slide('External GaAs data: a conditional reanalysis',31);
 txt(s,'Münzberg et al. (2022) measurements, reused under CC BY 4.0',64,135,1152,53,27,C.muted);
 table(s,[['Excitation separation','Our corrected HOM visibility','Conditional 95% interval'],...homAnalysis.cases.map(r=>[r.excitation_separation_ns.toFixed(1)+' ns',r.primary.corrected_visibility.toFixed(4),r.primary.corrected_interval95.map(v=>v.toFixed(4)).join(' to ')])],[320,405,427],209,255,25);
 txt(s,'39.4 ns: co-only normalization gives '+homAnalysis.cases[2].primary.co_only_corrected_visibility.toFixed(4),64,487,1152,55,29,C.teal,true);
 txt(s,'Source diagnosis needs calibrated controls',64,554,1152,51,29,C.ochre,true);
 footer(s,'Our ±2 ns windows and four reference peaks. Published corrections. Conditional counting/calibration errors exclude systematics.');
 note(s,'External GaAs data: a conditional reanalysis','Backup',
 'The real-data lesson is that a source-quality estimate depends on measurement controls. These are external Hong–Ou–Mandel histograms analyzed classically, not team measurements or a QRSM fit. We normalize central peaks to side peaks and apply published splitter and multiphoton corrections. The intervals exclude polarization, routing and drift systematics. At39.4nanoseconds, co-only normalization changes the estimate from0.7724to0.7938. That discrepancy guides checks of polarization, alignment and normalization before assigning a cause. The new joint-photon instrument supplies a mathematical candidate model, but these aggregate histograms lack the sequential records and source calibration needed to fit and test it. Repeated time-tagged acquisitions and held-out comparisons remain necessary. No microscopic cause, monotonic decay, reproduced author pipeline or improved device performance follows.',
 'quantum_dot_bridge/hom_analysis/results.json, PROTOCOL.md and independent review. Dataset https://doi.org/10.5281/zenodo.6337697, CC BY4.0, by Julian Munzberg, Franz Draxl, Saimon Filipe Covre da Silva, Yusuf Karli, Santanu Manna, Armando Rastelli, Gregor Weihs and Robert Keil. Paper https://arxiv.org/html/2203.08682v1 SectionIV Eqs3–4. Quoted paper V=.803(.005),.826(.004),.774(.004) remain separate. Our primary extraction uses half-open windows of half-width2ns, no background subtraction, reference cycle indices−2,−1,+1,+2 and200000Monte Carlo draws. R=.514±.007,g2=.016±.001, assumed independent but shared across separations. Data hashes verified against reference_hom/provenance_manifest.json. These aggregate histograms cannot provide original QRSM binary histories or uniquely identify charge traps.');
}

{
 const s=slide('The joint-photon QRSM observation model',32);
 txt(s,'A new complete-emission surrogate carries the hidden environment between pairs',64,135,1152,54,26,C.muted);
 table(s,[['Physical step','Digital representation','Retained information'],['Emit each photon','Complex wavepacket Gram modes','Photon modes + environment'],['Observe a photon pair','Controlled-SWAP parity = HOM statistic','Conditional environment state'],['Predict the next pair','Repeated completely positive maps','Dependence on the full record']],[300,475,377],209,246,24);
 txt(s,'Simulation, 64 pairs: 5.60% coherent flags, 4.50% classical false flags',64,483,1152,58,27,C.ochre,true);
 txt(s,'IBM four-pair flag-distribution TV: 0.249 coherent / 0.286 classical',64,557,1152,54,27,C.ink,true);
 footer(s,'TV is raw measured versus ideal flag probabilities, lower is closer. These tests do not identify a physical defect.');
 note(s,'The joint-photon QRSM observation model','Backup',
 'The missing observation model is now implemented. A fully excited emitter decays into a photon whose exponential temporal mode depends on the environmental state. Complex Gram overlaps embed the finite mode family exactly. A controlled-SWAP parity measurement equals the balanced-HOM symmetry statistic, and tracing the photon modes produces a conditional environmental map. Independent bosonic calculations check probabilities and conditional coherences. The environment persists between pairs. Passive outcomes cannot separate these hypotheses. A calibrated shift introduces a small joint effect, but the64pair simulated study gives only5.60percent coherent flags versus4.50percent classical false flags. The separate selected four-pair IBM circuits use22/29qubits and256/334nativeCZgates. Their raw flag distributions haveTV.249/.286, so implementation noise remains substantial. They do not validate the optical assumptions or certify quantum memory.',
 'quantum_dot_bridge/qrsm_hom_followup/README.md, physical_model.py, circuits.py, main/results.json and main/independent_review.json. Thirty thousand synthetic records replayed independently. Hardware current summary family_results.dot_selected_four_pair, selected_four_coherent and selected_four_classical,4096shots each. Distinct chosenθ3π/4,+2Γfour-pair control. Zconditional memory is not fullstate tomography. Main14circuit bundle uses earlierθπ/3. New source assumes full emission, fixed environment during each packet and controlled gaps. Original QRSM excitation-exchange dynamics are distinct. Measurement precedent Garcia-Escartin and Chamorro-Posada, https://arxiv.org/html/1303.6814v1.');
}
{
 const s=slide('More data helps only under trusted calibration',33);
 txt(s,'Selected control and ideal resets between independent four-pair blocks',64,135,1152,51,27,C.muted);
 table(s,[['Attempted pairs / record','Nominal coherent flags','Classical false flags'],...dotDesign.power_trials.map(r=>[r.attempted_pairs.toLocaleString('en-US'),pct(r.cases[0].flag_rate,2),pct(r.cases[1].flag_rate,2)])],[440,356,356],202,326,23);
 txt(s,'The stronger 8-state HMM predicts as well within uncertainty',64,550,1152,45,28,C.teal,true);
 footer(s,'At 7,644 pairs: changed collection gives 72% false flags, mode overlap 53.25%, readout 21.05%. Each cell: 2,000 records.');
 note(s,'More data helps only under trusted calibration','Backup',
 'After preserving the negative main result, an exact648setting scan selected a new control and gap rotation. A separate prospective simulation uses ideal resets between four-pair blocks and independently calibrated thresholds at every budget. At2584attempted pairs, nominal flags reach79.75percent with4.85percent classical false flags. The full budget curve remains visible. This is a different preparation protocol, not a tuned replacement of the64pair study. At7644pairs, changes in collection, mode overlap or readout give72,53.25and21.05percent false flags from still-classical sources. The8state HMM differs from the calibrated physical predictor by only0.0000092nats per pair, with an interval spanning zero. All20HMM starts reached the iteration cap. More data cannot repair a wrong measurement model, and no classical impossibility or physical defect follows.',
 'quantum_dot_bridge/qrsm_hom_followup/exploratory_design/README.md, design_results.json, VALIDATION_PROTOCOL.md, validation_run/results.json and independent_review.json. θ3π/4, second-emission shift+2Γ, eta.8, resetI/2 per4pair block. All lost pairs charged,2source excitations per pair. Independent20k training and20k predictive blocks,4/8state HMM10starts/200iterations. Rigorous simple-hypothesis bound1911blocks uses a different exact-model log4 threshold, not the empirical curves. No validated physical control/reset time.');
}
{
 const s=slide('Atomic and photon channels on IBM',34);
 txt(s,'Actual gate execution of bounded physical models, with raw readout retained',64,135,1152,53,27,C.muted);
 const ids=['atomic_d-5_Z','atomic_d+0_Z','atomic_d+5_Z'];
 table(s,[['Atomic detuning','Ideal excited probability','Raw IBM probability','95% shot interval'],...ids.map((id,i)=>{const r=hwChannels.rows.find(x=>x.name===id).observables;return[['−5 Hz','0 Hz','+5 Hz'][i],pct(r.ideal_system_zero_probability,2),pct(r.raw_system_zero_probability,2),r.raw_system_zero_wilson95.map(v=>pct(v,2)).join(' to ')];})],[270,320,280,282],203,251,24);
 txt(s,'Finite pulses and dissipation. 4 qubits, 22 native CZ gates.',64,482,1152,47,29,C.teal,true);
 txt(s,'Two-photon NOON at phase 0.35: raw occupation TV = 0.033',64,546,1152,65,28,C.ink,true);
 footer(s,'2,048 shots each. These are superconducting encodings, not measured atoms, photons or a 128-second optical monitor.');
 note(s,'Atomic and photon channels on IBM','Backup',
 'The atomic adapter exponentiates the actual driven Lindblad evolution through finite pulses and free precession, constructs its complete channel and synthesizes a Stinespring isometry. It does not rotate a qubit directly to an analytic output probability. Independent affine-Bloch calculations verify the ideal response. IBM results show the response direction but retain material bias, especially at the outer detunings. Separate photon circuits prepare actual finite mode states, apply phases, recombine and encode loss. A coherent source is represented by its unnormalized Poisson sectors throughN8; vacuum and the omitted tail remain charged. Raw occupancy moments include source failures. These are meaningful implementation tests, while acquisition, calibration and apparatus costs remain optical questions.',
 'hardware_campaign/optical_controls/README.md, PROTOCOL.md, models.py, bundle_v2/manifest.json and hardware_integration_review.json. hardware_campaign/runs/optical_controls_plain_v1/analysis.json,33science rows. Atomic originalT1=100s,T2=.2s,2.5ms pulses,20ms dark interval,1% preparation error; physical optical2/4%readout assumptions not added as if hardware correction. Coherent mean2before object, tailN>8=.0002374473, source/detection/object losses declared. Independent compiled mapping and moments audit passed.');
}
{
 const s=slide('Hardware coverage and circuit limits',35);
 txt(s,`${campaignNow.jobs} IBM jobs, ${campaignNow.science_circuit_executions} science executions, ${campaignNow.actual_campaign_quantum_seconds} charged QPU seconds`,64,135,1152,54,28,C.muted);
 table(s,[['Research family','What ran or was constructed','Boundary'],['Original QRSM','Full original suite, precision follow-up','Bias and routing still matter'],['Dot / atomic / photon models','Prepared states, channels and joint readout','Digital emulation, no optical setup'],['Spatial and long queries','Small models plus deeper stress tests','High acceptance can hide wrong answers'],['Full 49-cell process','389-qubit constructive circuit','Exceeds the 156-qubit device']],[310,480,362],204,327,24);
 txt(s,'All 25 research families have an explicit evidence and gap ledger',64,559,1152,51,29,C.teal,true);
 footer(s,'Classical fitting, published optical data and industrial process calibration remain distinct from superconducting execution.');
 note(s,'Hardware coverage and circuit limits','Backup',
 'Ten completed jobs execute207science circuits and40calibration circuits, totaling688640shots and244charged QPU seconds. These are circuit executions including repeats, not207independent discoveries. The campaign covers the original suite and meaningful rungs of circuit-ready families. Independent3/5/7site contacts compare enumeration and clean counters. The1024entry seeded-diagonal stress circuit reaches98,680nativeCZgates and46.58percent raw matches versus99.23percent ideal. It is distinct from semantic retrieval. Eight-step rounds and ten-step bounded rewinds test ingredients, not full adaptiveBBHT. Four-pair dot circuits use22/29qubits and a declared32entry flag-memory marginal. The389qubit49cell construction cannot fit156qubits. Classical benchmarks, published optical data and real process calibration remain separate requirements.',
 'hardware_campaign/results.json and RESULTS.md, all10job IDs with immutable plans/raw counts and exact ISAQPY. coverage.json and coverage.md; extensions/bundle_v1/manifest.json and independent_review.json; quantum_dot_bridge/qrsm_hom_followup/exploratory_design/HARDWARE_EXTENSION.md and hardware_bundle/manifest.json. Native counts differ from generic constructions. Z marginal checks are not full-state fidelity. Full49 results in finals-lithography/full_spatial_circuit/results.json.');
}

await fs.mkdir(build,{recursive:true});
for(let i=0;i<P.slides.items.length;i++){const b=await P.export({slide:P.slides.items[i],format:'png',scale:1});await fs.writeFile(`${build}/visual-slide-${String(i+1).padStart(2,'0')}.png`,new Uint8Array(await b.arrayBuffer()));}
await fs.writeFile(build+'/visual_notes.json',JSON.stringify(scripts,null,2));
const candidate=build+'/visual-candidate.pptx';await(await PresentationFile.exportPptx(P)).save(candidate);
if(!draft){
 const tableOwners=[3,4,14,15,16,17,18,19,20,21,23,24,25,26,27,28,29,30,31,32,33,34,35];
 const result=await finalizePresentation({workspaceDir:root,candidatePath:candidate,finalPath:process.env.OUTPUT_PPTX??root+'/finals-deck/Rewind_Amplify_Finals_Visual.pptx',pythonExecutable:py,integrityValidatorPath:skill+'/container_tools/inspect_presentation_package_integrity.py',layoutValidatorPath:skill+'/container_tools/inspect_presentation_layout_geometry.py',layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit',...tableOwners.flatMap(n=>['--require-native-table-slide',String(n)])],explicitTotalSlideCount:35,requiredNativeChartOwnerSlides:[5,8,11],requiredNativeTableOwnerSlides:tableOwners,materializeLiteralChartWorkbooks:true,fontPolicy:{basis:'design',families:['Arial']},verifyArtifactToolImport:true,receiptPath:process.env.OUTPUT_RECEIPT??build+'/visual_validation.json'});console.log(JSON.stringify(result));
}
console.log(JSON.stringify({draft,slides:P.slides.items.length,scriptCount:scripts.length}));
