"""Impulse blanking on I/Q and continuous overlap-add audio denoising."""
import numpy as np
from scipy.ndimage import binary_dilation, median_filter

class ImpulseBlanker:
    def process(self,x,enabled=False,strength=50):
        if not enabled or strength<=0:return x
        magnitude=np.abs(x);baseline=max(float(np.median(magnitude)),1e-5)
        threshold=baseline*(12-9*strength/100)
        bad=magnitude>threshold
        if not np.any(bad) or np.mean(bad)>.08:return x
        bad=binary_dilation(bad,iterations=1+round(strength/20))
        good=np.flatnonzero(~bad)
        if len(good)<len(x)*.8:return x
        positions=np.flatnonzero(bad);out=x.copy()
        out[bad]=np.interp(positions,good,x.real[good])+1j*np.interp(positions,good,x.imag[good])
        return out

class SpectralReducer:
    # 512 sample frames / 256 sample hops at 32 kHz. Dry and wet both have
    # the same 8 ms delay; toggling never drops or adds an audio block.
    def __init__(self):
        self.previous=np.zeros(256);self.overlap=np.zeros(256)
        self.window=np.sqrt(.5-.5*np.cos(2*np.pi*np.arange(512)/512))
        self.noise=None;self.gain=np.ones(257)
    def process(self,a,enabled=False,strength=40):
        if len(a)%256:raise ValueError('Audio block must contain complete 256 sample hops')
        result=[];amount=strength/100 if enabled else 0
        for start in range(0,len(a),256):
            hop=a[start:start+256];frame=np.r_[self.previous,hop];self.previous=hop.copy()
            spectrum=np.fft.rfft(frame*self.window);power=abs(spectrum)**2
            floor=median_filter(power,size=15,mode='nearest')*.8
            if self.noise is None:self.noise=floor
            else:
                alpha=np.where(floor<self.noise,.15,.008)
                self.noise+=alpha*(floor-self.noise)
            minimum=10**(-18*amount/20)
            target=np.sqrt(np.maximum(minimum**2,1-(.7+1.8*amount)*self.noise/np.maximum(power,1e-20))) if amount else np.ones_like(power)
            target=np.convolve(np.pad(target,(1,1),mode='edge'),[.2,.6,.2],mode='valid')
            self.gain=.75*self.gain+.25*target
            restored=np.fft.irfft(spectrum*self.gain,n=512)*self.window
            result.append(self.overlap+restored[:256]);self.overlap=restored[256:]
        return np.concatenate(result)
