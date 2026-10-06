'use strict';
class PCMPlayer {
 static async create(context){await context.audioWorklet.addModule('/pcm-worklet.js');return new PCMPlayer(context);}
 constructor(context){this.context=context;this.gain=context.createGain();this.gain.gain.value=.8;this.gain.connect(context.destination);this.node=new AudioWorkletNode(context,'hamtech-pcm',{numberOfInputs:0,numberOfOutputs:1,outputChannelCount:[1]});this.node.connect(this.gain);this._enabled=false;this.received=0;this.rms=0;this.underruns=0;this.overruns=0;this.buffered=0;this.node.port.onmessage=e=>{if(e.data.type==='stats'){this.underruns=e.data.underruns;this.overruns=e.data.overruns;this.buffered=e.data.buffered;}};}
 get enabled(){return this._enabled;}
 set enabled(value){this._enabled=Boolean(value);this.node.port.postMessage({type:'enable',value:this._enabled});}
 volume(value){this.gain.gain.setTargetAtTime(value,this.context.currentTime,.025);}
 stop(){this.enabled=false;}
 push(samples){this.received+=samples.length;let energy=0;for(const x of samples)energy+=x*x;this.rms=Math.sqrt(energy/Math.max(1,samples.length));if(!this.enabled||this.context.state!=='running')return;this.node.port.postMessage({type:'pcm',samples},[samples.buffer]);}
}
