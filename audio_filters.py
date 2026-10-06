"""Stateful 32 kHz audio notch filters with smooth bypass transitions."""
import numpy as np
from scipy import signal

class NotchStage:
    def __init__(self):
        self.coeff=None;self.zi=np.zeros(2);self.wet=0.;self.target=0.;self.old=None
    def tune(self,hz,width):
        coeff=signal.iirnotch(hz,hz/width,fs=32000)
        if self.coeff is not None:
            self.old=(self.coeff,self.zi.copy())
        self.coeff=coeff;self.zi=np.zeros(2)
    def process(self,a):
        if self.coeff is None:return a
        filtered,self.zi=signal.lfilter(*self.coeff,a,zi=self.zi)
        if self.old is not None:
            coeff,zi=self.old;old,_=signal.lfilter(*coeff,a,zi=zi)
            fade=np.linspace(0,1,len(a));filtered=old*(1-fade)+filtered*fade;self.old=None
        next_wet=self.target
        fade=np.linspace(self.wet,next_wet,len(a));self.wet=next_wet
        return a+(filtered-a)*fade

class AudioNotches:
    def __init__(self,mode):
        self.mode=mode;self.manual=NotchStage();self.auto=NotchStage()
        self.manual_settings=None;self.anf=False;self.history=np.zeros(4096)
        self.count=0;self.candidate=None;self.hits=0;self.misses=0;self.auto_hz=None
        self.window=np.hanning(4096)
    def configure(self,anf=False,notch=False,notch_hz=1000,notch_width=80):
        setting=(notch_hz,notch_width)
        if setting!=self.manual_settings:
            self.manual.tune(*setting);self.manual_settings=setting
        self.manual.target=float(notch)
        enabled=bool(anf) and self.mode in ('LSB','USB','AM','NFM')
        if enabled!=self.anf:
            self.auto.target=0.;self.candidate=None;self.hits=0;self.misses=0
            self.history[:]=0;self.auto_hz=None
        self.anf=enabled
    def process(self,a):
        if self.anf:
            self.history=np.roll(self.history,-len(a));self.history[-len(a):]=a
            self.count+=1
            if self.count%4==0:self.detect()
        a=self.auto.process(a)
        return self.manual.process(a)
    def detect(self):
        power=abs(np.fft.rfft(self.history*self.window))**2
        lo,hi=round(200*4096/32000),round(4500*4096/32000)
        k=lo+int(np.argmax(power[lo:hi]));neighbours=np.r_[power[max(lo,k-18):max(lo,k-3)],power[min(hi,k+4):min(hi,k+19)]]
        # Only a strong, spectrally narrow and persistent line is a candidate.
        narrow=power[max(0,k-2):k+3].sum()/max(power[lo:hi].sum(),1e-20)
        ratio=power[k]/max(float(np.median(neighbours)),1e-16)
        if ratio>100 and narrow>.3 and power[k]>1e-7:
            log=np.log(np.maximum(power[k-1:k+2],1e-20));den=log[0]-2*log[1]+log[2]
            delta=.5*(log[0]-log[2])/den if abs(den)>1e-12 else 0
            hz=(k+float(np.clip(delta,-.5,.5)))*32000/4096
            self.hits=self.hits+1 if self.candidate is not None and abs(hz-self.candidate)<25 else 1
            self.candidate=hz;self.misses=0
            if self.hits>=3:
                if self.auto_hz is None or abs(hz-self.auto_hz)>10:
                    self.auto.tune(hz,70);self.auto_hz=hz
                self.auto.target=1.
        else:
            self.hits=0;self.misses+=1
            if self.misses>=3:self.auto.target=0.;self.auto_hz=None
