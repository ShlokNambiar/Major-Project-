// Builds presentation/progress_update.pptx (pptxgenjs). Run: cd presentation && npm i pptxgenjs && node build_deck.js
// Numbers: final 14-attack results (results/results_v2.json) plus the 18-attack Sybil extension (results/results_v18_final.json, paper/tables_v18.tex). Do not edit numbers by hand without checking those.
const pptxgen = require("pptxgenjs");
const pres = new pptxgen(); pres.layout = "LAYOUT_16x9";
const NAVY="0B1F33", TEAL="1C7C7D", AMBER="F2A541", INK="1B2A38", MUTED="5B6B7A", PALE="EAF2F3", WHITE="FFFFFF", RED="C0392B";
const HF="Cambria", BF="Calibri";
const title=(s,t)=>s.addText(t,{x:0.6,y:0.35,w:8.8,h:0.7,fontFace:HF,fontSize:30,bold:true,color:NAVY,margin:0,isTextBox:true});
const card=(s,x,y,w,h,head,body,fill=PALE,fs=14)=>{
  s.addShape(pres.ShapeType.roundRect,{x,y,w,h,fill:{color:fill},line:{color:fill},rectRadius:0.08,objectName:"card"});
  s.addText(head,{x:x+0.2,y:y+0.15,w:w-0.4,h:0.4,fontFace:HF,fontSize:16,bold:true,color:TEAL,margin:0,isTextBox:true});
  s.addText(body,{x:x+0.2,y:y+0.6,w:w-0.4,h:h-0.75,fontFace:BF,fontSize:fs,color:INK,margin:0,valign:"top",isTextBox:true});
};
const H=(t)=>({text:t,options:{bold:true,color:WHITE,fill:{color:NAVY},fontFace:BF,fontSize:12,align:"center"}});
const R=(t,b)=>({text:t,options:{fontFace:BF,fontSize:12,color:INK,align:"center",bold:!!b}});
const RL=(t,b)=>({text:t,options:{fontFace:BF,fontSize:12,color:INK,align:"left",bold:!!b}});
const TB={border:{type:"solid",color:"D5DDE3",pt:0.75}};
const foot=(s,t)=>s.addText(t,{x:0.6,y:4.95,w:8.8,h:0.4,fontFace:BF,fontSize:10.5,italic:true,color:MUTED,margin:0,isTextBox:true});

// 1 title
let s=pres.addSlide(); s.background={color:NAVY};
s.addText("Neighbourhood-aware misbehaviour detection for V2X",{x:0.7,y:1.2,w:8.6,h:1.5,fontFace:HF,fontSize:38,bold:true,color:WHITE,margin:0,isTextBox:true});
s.addText("Final results on 14 attack types, extended to 18 with Sybil",{x:0.7,y:2.9,w:8.6,h:0.5,fontFace:BF,fontSize:20,color:AMBER,margin:0,isTextBox:true});
s.addText("Evaluated on the VeReMi Extension benchmark (simulated traffic, Zenodo 20090854)",{x:0.7,y:3.5,w:8.6,h:0.4,fontFace:BF,fontSize:15,color:"CADCFC",margin:0,isTextBox:true});
s.addNotes("Final update. All numbers are on a simulated benchmark, not real-world traffic. Paper: paper/main.pdf (IEEE conference, 6 pages, 18 references).");

// 2 problem + idea
s=pres.addSlide(); s.background={color:WHITE}; title(s,"The idea: judge a sender by its neighbours");
card(s,0.6,1.3,4.2,3.5,"Problem","Vehicles broadcast position, speed and heading. A misbehaving vehicle sends false data (wrong position, speed, a fake stop) that can mislead the cars around it.");
card(s,5.2,1.3,4.2,3.5,"Our approach","A small transformer looks at each sender over time and at the other senders nearby (neighbour attention), so it can spot a sender whose claims do not fit its surroundings.");
s.addNotes("Per-sender view vs neighbourhood-aware view; neighbour attention is the part we test with an ablation.");

// 3 what was built
s=pres.addSlide(); s.background={color:WHITE}; title(s,"What was built");
const items=[
 ["Data","VeReMi Extension: 14 of 19 attack types for the main results; extended to 18 of 19 with the four Sybil attacks (RandomSpeedOffset archive excluded as mislabeled)"],
 ["Splits","Train 109,823 / validation 29,547 / test 68,971 windows; 2 seeds"],
 ["Final model (v2)","Transformer, 144k parameters, temporal + neighbour attention; 9 claim values + 10 plausibility checks per message"],
 ["Checks and training","Kinematics, road map learned from honest traffic, nearest other claim, self-repeat, copied trail; training adds injected lies (offset, fake stop); receiver-side memory"]];
items.forEach((it,i)=>{const y=1.2+i*0.95;
  s.addShape(pres.ShapeType.ellipse,{x:0.6,y:y,w:0.6,h:0.6,fill:{color:TEAL},line:{color:TEAL},objectName:"num"});
  s.addText(String(i+1),{x:0.6,y:y,w:0.6,h:0.6,align:"center",valign:"middle",fontFace:HF,fontSize:20,bold:true,color:WHITE,margin:0,isTextBox:true});
  s.addText(it[0],{x:1.45,y:y-0.04,w:7.9,h:0.3,fontFace:HF,fontSize:17,bold:true,color:NAVY,margin:0,isTextBox:true});
  s.addText(it[1],{x:1.45,y:y+0.28,w:7.9,h:0.5,fontFace:BF,fontSize:13,color:MUTED,margin:0,valign:"top",isTextBox:true});});

// 4 main results
s=pres.addSlide(); s.background={color:WHITE}; title(s,"Results on the test set (14 attacks)");
s.addTable([[H("Model"),H("Labels"),H("Precision"),H("Recall"),H("F1"),H("Accuracy")],
 [RL("Speed-check rule"),R("vehicle / message"),R("-"),R("-"),R("78.9 / 80.0"),R("-")],
 [RL("First model (no checks)"),R("vehicle"),R("98.4"),R("91.6"),R("94.9"),R("96.9")],
 [RL("v2"),R("vehicle"),R("98.65"),R("95.41"),R("97.01"),R("98.14")],
 [RL("v2 + memory"),R("vehicle"),R("-"),R("96.09"),R("97.12"),R("98.20")],
 [RL("v2",1),R("message",1),R("98.65",1),R("97.12",1),R("97.88",1),R("98.69",1)],
 [RL("v2 + memory",1),R("message",1),R("98.16",1),R("97.78",1),R("97.97",1),R("98.74",1)]],
 {x:0.6,y:1.2,w:8.8,colW:[2.3,1.6,1.2,1.2,1.3,1.2],rowH:0.36,...TB});
s.addText("False-positive rate: v2 0.60% (first model 0.7%)",{x:0.6,y:3.9,w:8.8,h:0.35,fontFace:BF,fontSize:14,bold:true,color:TEAL,margin:0,isTextBox:true});
s.addText("Message labels count an attacker only in windows where it sent a falsified message (dataset ground truth). Vehicle labels count every window of an attacker vehicle, including its honest-looking ones, so recall is lower.",{x:0.6,y:4.25,w:8.8,h:0.65,fontFace:BF,fontSize:12,color:INK,margin:0,valign:"top",isTextBox:true});
foot(s,"All values in %. Mean of 2 seeds. '-' = not reported for that row.");
s.addNotes("Both label schemes are shown on purpose; message labels match how the dataset marks lies, vehicle labels are the stricter view.");

// 5 neighbour attention
s=pres.addSlide(); s.background={color:WHITE}; title(s,"What neighbour attention adds");
card(s,0.6,1.25,2.8,3.5,"Small but real","+0.3 F1 points (95% CI about [0.2, 0.4]). Significant on 8-10 of the 14 attacks.");
card(s,3.6,1.25,2.8,3.5,"Fewer false alarms","False-positive rate drops from 0.90% to 0.60% with neighbour attention.");
card(s,6.6,1.25,2.8,3.5,"Fails with attacker majority","When attackers are most of a sender's neighbours the gain shrinks and turns negative (-0.004 within-attack). First model: +0.071 down to -0.023.","FBEFD9");
s.addNotes("Be upfront: neighbour attention is a modest gain, and it depends on honest neighbours being the majority.");

// 6 detection speed
s=pres.addSlide(); s.background={color:WHITE}; title(s,"How fast attackers are flagged (v2)");
[["0.9 s","mean time to first alarm"],["0 s","median time to first alarm"],["96%","of attacker-receiver pairs flagged"]].forEach((t,i)=>{
 const x=0.6+i*3.0;
 s.addShape(pres.ShapeType.roundRect,{x,y:1.4,w:2.8,h:2.4,fill:{color:PALE},line:{color:PALE},rectRadius:0.08,objectName:"card"});
 s.addText(t[0],{x:x+0.2,y:1.7,w:2.4,h:0.9,fontFace:HF,fontSize:44,bold:true,color:NAVY,margin:0,isTextBox:true});
 s.addText(t[1],{x:x+0.2,y:2.7,w:2.4,h:0.8,fontFace:BF,fontSize:14,color:INK,margin:0,valign:"top",isTextBox:true});});
s.addText("Most attackers are caught in the first window they appear in; a few take longer and pull the mean up.",{x:0.6,y:4.1,w:8.8,h:0.6,fontFace:BF,fontSize:14,color:INK,margin:0,valign:"top",isTextBox:true});
s.addNotes("Latency counts from the first window that contains the attacker, per receiver.");

// 7 collusion stress test
s=pres.addSlide(); s.background={color:WHITE}; title(s,"Stress test: colluding attackers");
s.addTable([[H("Consistent lie (colluders)"),H("First model"),H("v2")],
 [RL("50 m position offset"),R("<= 0.04"),R("0.83-0.86",1)],
 [RL("Fake stop"),R("<= 0.04"),R("about 0.70",1)],
 [RL("Spoofed convoy (never seen in training)"),R("<= 0.04"),R("0.87-0.90",1)],
 [RL("Offset along the road (map-aware)"),R("<= 0.04"),R("0.23-0.25")],
 [RL("Convoy on own road (map-aware)"),R("<= 0.04"),R("0.36-0.48")]],
 {x:0.6,y:1.2,w:8.8,colW:[4.4,2.2,2.2],rowH:0.4,...TB});
s.addText("Colluder recall at a matched 1% false-positive rate. Coordinated convoys also raised the first model's honest false-positive rate from 0.9% to 3.0%.",{x:0.6,y:3.75,w:8.8,h:0.6,fontFace:BF,fontSize:13,color:INK,margin:0,valign:"top",isTextBox:true});
s.addText("Lies that stay on the road map are still hard: they need an independent signal (signal strength, sensors, roadside units).",{x:0.6,y:4.35,w:8.8,h:0.6,fontFace:BF,fontSize:13,bold:true,color:RED,margin:0,valign:"top",isTextBox:true});
s.addNotes("Injected collusion on top of VeReMi; the dataset itself has no colluding attackers.");

// 8 reference comparison
s=pres.addSlide(); s.background={color:WHITE}; title(s,"Against the reference paper");
s.addChart(pres.charts.BAR,[
 {name:"Reference (97.37%)",labels:["Precision","Recall","F1","Accuracy"],values:[97.37,97.37,97.37,97.37]},
 {name:"v2 + memory, message labels",labels:["Precision","Recall","F1","Accuracy"],values:[98.16,97.78,97.97,98.74]}],
 {x:0.5,y:1.15,w:5.8,h:3.7,barDir:"col",chartColors:["9AA9B5",TEAL],valAxisMinVal:95,valAxisMaxVal:100,valAxisMajorUnit:1,
  showValue:true,dataLabelFormatCode:"0.00",dataLabelFontSize:9,dataLabelColor:INK,dataLabelPosition:"outEnd",
  catAxisLabelColor:INK,valAxisLabelColor:MUTED,catAxisLabelFontSize:12,valAxisLabelFontSize:11,valAxisLabelFormatCode:"0",
  valGridLine:{color:"E3E8EC",size:0.5},catGridLine:{style:"none"},showLegend:true,legendPos:"b",legendFontSize:11,legendColor:INK});
s.addText("Abdel Hakeem & Kim, IEEE T-ITS 26(8), 2025 (survey), Table XIII: 97.37% for VeReMi, one number for accuracy, precision, recall and F1.",{x:6.6,y:1.2,w:2.9,h:1.5,fontFace:BF,fontSize:12,color:INK,margin:0,valign:"top",isTextBox:true});
s.addText("Not like-for-like: that figure is on the original VeReMi (5 attacks) and its source is not cited. Under vehicle labels our recall (96.09) and F1 (97.12) are below it.",{x:6.6,y:2.8,w:2.9,h:2.0,fontFace:BF,fontSize:12,italic:true,color:RED,margin:0,valign:"top",isTextBox:true});
s.addNotes("Report the comparison with its caveat; do not claim we beat the reference outright. This chart is the 14-attack system; on 18 attacks (with Sybil) all four numbers are below 97.37, see next slide.");

// 9 Sybil extension (18 attacks)
s=pres.addSlide(); s.background={color:WHITE}; title(s,"Extension: 18 attacks, including Sybil");
s.addTable([[H("18 attacks, 88,695 test windows"),H("Precision"),H("Recall"),H("F1"),H("Accuracy")],
 [RL("Ours, message labels",1),R("96.30",1),R("95.46",1),R("95.88",1),R("97.04",1)],
 [RL("Ours, vehicle labels"),R("96.33"),R("94.44"),R("95.38"),R("96.66")],
 [RL("No neighbour attention, message"),R("96.28"),R("92.69"),R("94.45"),R("96.07")]],
 {x:0.6,y:1.15,w:5.6,colW:[2.4,0.8,0.8,0.8,0.8],rowH:0.34,...TB});
s.addTable([[H("Sybil attack"),H("Recall")],
 [RL("GridSybil (largest, 20,598 slots)"),R("0.823",1)],
 [RL("DataReplaySybil"),R("0.914")],
 [RL("DoSDisruptiveSybil"),R("0.969")],
 [RL("DoSRandomSybil"),R("0.997")]],
 {x:6.45,y:1.15,w:3.0,colW:[2.2,0.8],rowH:0.34,...TB});
s.addText([
 {text:"Senders are tracked by pseudonym (what a receiver sees); three new inputs: identity age, handover distance, lockstep. Final = mean of 3 models. Message-label FPR 2.07%.",options:{breakLine:true}},
 {text:"Neighbour attention helps more with Sybil: +1.4 F1 (vs +0.3 on 14 attacks).",options:{bold:true,color:TEAL,breakLine:true}},
 {text:"Honest result: on 18 attacks all four numbers are below the 97.37% reference. Missed GridSybil ghosts look honest on every content check; they need an independent signal.",options:{bold:true,color:RED}}],
 {x:0.6,y:3.0,w:8.85,h:1.9,fontFace:BF,fontSize:13,color:INK,margin:0,valign:"top",paraSpaceAfter:6,isTextBox:true});
foot(s,"All values in % except recall per attack (message labels). Source: results/results_v18_final.json, paper/tables_v18.tex.");
s.addNotes("The 14-attack results are unchanged. Sybil makes the task harder: fake identities are separate senders. On the 14 original attack runs this model's FPR is 1.6% (vs 0.6% for the 14-attack model) because it lowers its threshold to catch ghosts. A bigger model alone and receiver memory did not help.");

// 10 next steps
s=pres.addSlide(); s.background={color:NAVY};
s.addText("Open items and next steps",{x:0.6,y:0.35,w:8.8,h:0.7,fontFace:HF,fontSize:30,bold:true,color:WHITE,margin:0,isTextBox:true});
const left=["GridSybil ghosts that look honest on every content check (recall 0.823)","Check on original VeReMi and VeReMi NextGen","Run v2 on dense traffic; add a 3rd seed","On-road consistent lies need an independent signal: signal strength, on-board sensors, roadside units","Paper done: paper/main.pdf, IEEE conference format, 6 pages, 18 references"];
s.addText(left.map((t,i)=>({text:t,options:{bullet:true,breakLine:i<left.length-1,paraSpaceAfter:10}})),{x:0.6,y:1.3,w:8.8,h:3.6,fontFace:BF,fontSize:18,color:WHITE,margin:0,valign:"top",isTextBox:true});
pres.writeFile({fileName:"progress_update.pptx"}).then(()=>console.log("written"));
