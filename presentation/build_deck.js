// Builds presentation/progress_update.pptx (pptxgenjs). Run: npm i pptxgenjs && node presentation/build_deck.js. NOTE: numbers in this deck are the OLD 2-attack results (see HANDOFF.md).
const pptxgen = require("pptxgenjs");
const pres = new pptxgen(); pres.layout = "LAYOUT_16x9";
const NAVY="0B1F33", TEAL="1C7C7D", AMBER="F2A541", INK="1B2A38", MUTED="5B6B7A", PALE="EAF2F3", WHITE="FFFFFF", RED="C0392B";
const HF="Cambria", BF="Calibri";
const title=(s,t)=>s.addText(t,{x:0.6,y:0.35,w:8.8,h:0.7,fontFace:HF,fontSize:32,bold:true,color:NAVY,margin:0,isTextBox:true});
const card=(s,x,y,w,h,head,body,fill=PALE)=>{
  s.addShape(pres.ShapeType.roundRect,{x,y,w,h,fill:{color:fill},line:{color:fill},rectRadius:0.08,objectName:"card"});
  s.addText(head,{x:x+0.2,y:y+0.15,w:w-0.4,h:0.4,fontFace:HF,fontSize:16,bold:true,color:TEAL,margin:0,isTextBox:true});
  s.addText(body,{x:x+0.2,y:y+0.6,w:w-0.4,h:h-0.75,fontFace:BF,fontSize:14,color:INK,margin:0,valign:"top",isTextBox:true});
};

// 1 title
let s=pres.addSlide(); s.background={color:NAVY};
s.addText("Neighbourhood-aware misbehavior detection for V2X",{x:0.7,y:1.3,w:8.6,h:1.5,fontFace:HF,fontSize:40,bold:true,color:WHITE,margin:0,isTextBox:true});
s.addText("Work in progress: preliminary results and next steps",{x:0.7,y:3.0,w:8.6,h:0.5,fontFace:BF,fontSize:20,color:AMBER,margin:0,isTextBox:true});
s.addText("Evaluated on the public VeReMi Extension benchmark",{x:0.7,y:3.6,w:8.6,h:0.4,fontFace:BF,fontSize:16,color:"CADCFC",margin:0,isTextBox:true});
s.addNotes("Status update. Real-data results exist for two attack types; extended metrics requested by the professor are still running.");

// 2 problem + idea
s=pres.addSlide(); s.background={color:WHITE}; title(s,"The idea: judge a sender by its neighbours");
card(s,0.6,1.3,4.2,3.5,"Problem","Vehicles broadcast position, speed and heading. A misbehaving vehicle sends false data (wrong position or speed) that can mislead others, for example hide a car that is closing in.");
card(s,5.2,1.3,4.2,3.5,"Our approach","A transformer looks at the 16 nearest senders over a 10-second window, so it can spot a sender that disagrees with its surroundings. Baseline: judge each sender alone.");
s.addNotes("Per-sender baseline vs neighbourhood-aware model with spatial interaction; ablation without spatial interaction.");

// 3 what is built
s=pres.addSlide(); s.background={color:WHITE}; title(s,"What is done so far");
const items=[["Model","Transformer with temporal and spatial attention, plus ablations"],["Data loader","Fixed for the real VeReMi format: message types and labels from filenames"],["Benchmark data","VeReMi Extension (simulated traffic) from Zenodo: RandomPos and ConstSpeed attacks"],["Experiments","3 models x 3 seeds, train on first hour, test on later hour"]];
items.forEach((it,i)=>{const y=1.3+i*0.95;
  s.addShape(pres.ShapeType.ellipse,{x:0.6,y:y,w:0.6,h:0.6,fill:{color:TEAL},line:{color:TEAL},objectName:"num"});
  s.addText(String(i+1),{x:0.6,y:y,w:0.6,h:0.6,align:"center",valign:"middle",fontFace:HF,fontSize:20,bold:true,color:WHITE,margin:0,isTextBox:true});
  s.addText(it[0],{x:1.45,y:y-0.02,w:7.9,h:0.3,fontFace:HF,fontSize:18,bold:true,color:NAVY,margin:0,isTextBox:true});
  s.addText(it[1],{x:1.45,y:y+0.3,w:7.9,h:0.35,fontFace:BF,fontSize:14,color:MUTED,margin:0,isTextBox:true});});

// 4 results chart
s=pres.addSlide(); s.background={color:WHITE}; title(s,"Preliminary results (F1)");
s.addChart(pres.charts.BAR,[
 {name:"Per-sender",labels:["RandomPos","ConstSpeed","Overall"],values:[0.970,0.960,0.973]},
 {name:"No spatial interaction",labels:["RandomPos","ConstSpeed","Overall"],values:[0.983,0.947,0.982]},
 {name:"Full model",labels:["RandomPos","ConstSpeed","Overall"],values:[0.987,0.948,0.982]}],
 {x:0.5,y:1.15,w:6.0,h:3.9,barDir:"col",chartColors:["9AA9B5",AMBER,TEAL],valAxisMinVal:0.9,valAxisMaxVal:1.0,valAxisMajorUnit:0.02,
  showValue:true,dataLabelFormatCode:"0.000",dataLabelFontSize:9,dataLabelColor:INK,dataLabelPosition:"outEnd",
  catAxisLabelColor:INK,valAxisLabelColor:MUTED,catAxisLabelFontSize:12,valAxisLabelFontSize:11,valAxisLabelFormatCode:"0.00",
  valGridLine:{color:"E3E8EC",size:0.5},catGridLine:{style:"none"},showLegend:true,legendPos:"b",legendFontSize:11,legendColor:INK});
s.addText("0.982",{x:6.8,y:1.3,w:2.7,h:0.8,fontFace:HF,fontSize:54,bold:true,color:TEAL,margin:0,isTextBox:true});
s.addText("overall F1, full model (baseline 0.973)",{x:6.8,y:2.1,w:2.7,h:0.6,fontFace:BF,fontSize:14,color:INK,margin:0,isTextBox:true});
s.addText("AUC about 0.997 for all models. Mean of 3 seeds; std 0.001 to 0.004.",{x:6.8,y:3.0,w:2.7,h:0.9,fontFace:BF,fontSize:12,color:MUTED,margin:0,isTextBox:true});
s.addNotes("Gap overall is about 0.9 F1 points; RandomPos about 1.7 points. ConstSpeed is slightly worse with neighbours.");

// 5 takeaways
s=pres.addSlide(); s.background={color:WHITE}; title(s,"What the results say");
card(s,0.6,1.3,2.8,3.4,"Neighbours help","Overall F1 +0.9 points; RandomPos +1.7 points over the per-sender baseline.");
card(s,3.6,1.3,2.8,3.4,"Spatial adds little","Full model ties the no-spatial variant overall (0.982). It helps only on RandomPos.");
card(s,6.6,1.3,2.8,3.4,"ConstSpeed is worse","0.948 vs 0.960 for the baseline. We report this negative result.","FBEFD9");
s.addNotes("Be upfront about the ConstSpeed dip and the limited attack coverage.");

// 6 full metrics
s=pres.addSlide(); s.background={color:WHITE}; title(s,"Preliminary: full metrics and latency");
const H=(t)=>({text:t,options:{bold:true,color:WHITE,fill:{color:NAVY},fontFace:BF,fontSize:13,align:"center"}});
const R=(t,b)=>({text:t,options:{fontFace:BF,fontSize:13,color:INK,align:"center",bold:!!b}});
const RL=(t)=>({text:t,options:{fontFace:BF,fontSize:13,color:INK,align:"left"}});
s.addTable([[H("Model"),H("Precision"),H("Recall"),H("F1"),H("False-pos. rate")],
 [RL("Per-sender"),R("0.987"),R("0.959"),R("0.973"),R("0.5%")],
 [RL("Full model"),R("0.989",1),R("0.975",1),R("0.982",1),R("0.5%",1)]],
 {x:0.6,y:1.3,w:8.8,colW:[2.4,1.6,1.6,1.6,1.6],rowH:0.42,border:{type:"solid",color:"D5DDE3",pt:0.75}});
s.addText("Detection latency",{x:0.6,y:2.85,w:8.8,h:0.35,fontFace:HF,fontSize:18,bold:true,color:TEAL,margin:0,isTextBox:true});
[["0.15 s","mean time to first alarm, full model (baseline 0.70 s)"],["99%","of malicious sender-receiver pairs eventually flagged (baseline 96%)"],["0 s","90th percentile for the full model (baseline 3 s)"]].forEach((t,i)=>{
 const x=0.6+i*3.0;
 s.addText(t[0],{x,y:3.25,w:2.8,h:0.7,fontFace:HF,fontSize:36,bold:true,color:NAVY,margin:0,isTextBox:true});
 s.addText(t[1],{x,y:3.95,w:2.7,h:0.7,fontFace:BF,fontSize:12,color:INK,margin:0,valign:"top",isTextBox:true});});
s.addText("Latency counts from the first window that contains the sender; each window needs about 10 s of history. Mean of 3 seeds.",{x:0.6,y:4.8,w:8.8,h:0.4,fontFace:BF,fontSize:11,italic:true,color:MUTED,margin:0,isTextBox:true});
s.addNotes("Addresses professor point 1: precision, recall, F1, FPR and detection latency.");

// 7 malicious neighbours
s=pres.addSlide(); s.background={color:WHITE}; title(s,"When neighbours are malicious too");
const bl=["0-10%","10-30%","30-50%","50-100%"];
s.addChart(pres.charts.BAR,[
 {name:"Per-sender",labels:bl,values:[0.956,0.966,0.959,0.953]},
 {name:"Full model",labels:bl,values:[0.973,0.981,0.974,0.971]}],
 {x:0.5,y:1.15,w:5.8,h:3.7,barDir:"col",chartColors:["9AA9B5",TEAL],valAxisMinVal:0.9,valAxisMaxVal:1.0,valAxisMajorUnit:0.02,
  showValue:true,dataLabelFormatCode:"0.000",dataLabelFontSize:9,dataLabelColor:INK,dataLabelPosition:"outEnd",
  catAxisLabelColor:INK,valAxisLabelColor:MUTED,catAxisLabelFontSize:12,valAxisLabelFontSize:11,valAxisLabelFormatCode:"0.00",
  showCatAxisTitle:true,catAxisTitle:"Share of a sender's neighbours that are malicious",catAxisTitleFontSize:11,catAxisTitleColor:MUTED,
  showValAxisTitle:true,valAxisTitle:"Recall",valAxisTitleFontSize:11,valAxisTitleColor:MUTED,
  valGridLine:{color:"E3E8EC",size:0.5},catGridLine:{style:"none"},showLegend:true,legendPos:"b",legendFontSize:11,legendColor:INK});
s.addText("Recall barely moves, and false alarms do not rise, even when over half of the neighbours are attackers (0.971 vs 0.973 for the cleanest case).",{x:6.6,y:1.3,w:2.9,h:1.9,fontFace:BF,fontSize:14,color:INK,margin:0,valign:"top",isTextBox:true});
s.addText("Caveat: attackers here act independently (about 30%). Colluding attackers, and crash intent, are not modelled in VeReMi.",{x:6.6,y:3.4,w:2.9,h:1.4,fontFace:BF,fontSize:12,italic:true,color:MUTED,margin:0,valign:"top",isTextBox:true});
s.addNotes("Addresses professor point 2. Recall by share of malicious neighbours; false-positive rate stays below 0.8% in every bucket.");

// 7 what's left
s=pres.addSlide(); s.background={color:NAVY};
s.addText("What is left",{x:0.6,y:0.35,w:8.8,h:0.7,fontFace:HF,fontSize:32,bold:true,color:WHITE,margin:0,isTextBox:true});
const left=["Add more attack types: position offsets, DoS, Sybil (2 of about 20 so far)","Rerun domain-transfer experiment on the benchmark","Test colluding attackers and the spoofed-approach (crash) scenario","Update paper text and tables to the real results"];
s.addText(left.map((t,i)=>({text:t,options:{bullet:true,breakLine:i<left.length-1,paraSpaceAfter:10}})),{x:0.6,y:1.3,w:8.8,h:3.4,fontFace:BF,fontSize:18,color:WHITE,margin:0,valign:"top",isTextBox:true});
pres.writeFile({fileName:"progress_update.pptx"}).then(()=>console.log("written"));
