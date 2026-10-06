'use strict';
class HamTechPCM extends AudioWorkletProcessor {
 constructor(){super();this.ring=new Float32Array(96000);this.write=0;this.read=0;this.target=8640;this.enabled=false;this.ready=false;this.underruns=0;this.overruns=0;this.fade=0;this.last=0;this.frames=0;this.port.onmessage=e=>{const m=e.data;if(m.type==='enable'){this.enabled=m.value;this.write=0;this.read=0;this.ready=false;this.fade=0;this.last=0;}else if(m.type==='pcm'&&this.enabled){const a=m.samples;for(let i=0;i<a.length;i++)this.ring[(this.write++)%this.ring.length]=a[i];if(this.write-this.read>24000){this.read=this.write-this.target;this.ready=false;this.fade=0;this.overruns++;}}};}
 process(inputs,outputs){const channels=outputs[0];if(!channels?.length)return true;const out=channels[0];for(let i=0;i<out.length;i++){
  if(!this.enabled){out[i]=0;continue;}
  const available=this.write-this.read;
  if(!this.ready&&available>=this.target){this.ready=true;this.fade=0;}
  if(!this.ready){this.last*=.98;out[i]=this.last;continue;}
  if(available<3){this.ready=false;this.underruns++;this.last*=.98;out[i]=this.last;continue;}
  const index=Math.floor(this.read),fraction=this.read-index,a=this.ring[index%this.ring.length],b=this.ring[(index+1)%this.ring.length];
  this.fade=Math.min(1,this.fade+1/256);this.last=(a+(b-a)*fraction)*this.fade;out[i]=this.last;
  const correction=Math.max(-.002,Math.min(.002,(available-this.target)/this.target*.002));this.read+=48000/sampleRate*(1+correction);
 }
 for(let c=1;c<channels.length;c++)channels[c].set(out);this.frames+=out.length;if(this.frames>=sampleRate/2){this.frames=0;this.port.postMessage({type:'stats',underruns:this.underruns,overruns:this.overruns,buffered:Math.max(0,Math.round(this.write-this.read)),ready:this.ready});}return true;
 }
}
registerProcessor('hamtech-pcm',HamTechPCM);
