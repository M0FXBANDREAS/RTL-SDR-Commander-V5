import numpy as np
from scipy import signal
from audio_filters import AudioNotches
from noise_filters import ImpulseBlanker, SpectralReducer
RATE=1024000
BLOCK=32768
FFT_SIZE=8192
class DSP:
    def __init__(self, mode='LSB', bandwidth=2400, offset=0):
        self.mode, self.bandwidth = mode, bandwidth
        self.offset=offset
        self.mix=np.exp(2j*np.pi*offset*np.arange(BLOCK)/RATE) if offset else None
        self.osc_phase=1+0j
        self.front = signal.firwin(129, 110000, fs=RATE)
        self.front_state = np.zeros(128, complex)
        cutoff = bandwidth / 2
        if mode in ('LSB', 'USB'):
            # Complex FIR selects only one sideband, with 150 Hz carrier rejection.
            half = (bandwidth - 150) / 2
            center = (bandwidth + 150) / 2 * (1 if mode == 'USB' else -1)
            n = np.arange(1025) - 512
            self.channel = signal.firwin(1025, half, fs=256000) * np.exp(2j*np.pi*center*n/256000)
        else:
            self.channel = signal.firwin(1025, min(100000, max(125, cutoff)), fs=256000)
        self.channel_state = np.zeros(len(self.channel)-1, complex)
        self.audio_filter = signal.butter(5, 15000 if mode == 'WFM' else min(12000, max(1000, bandwidth)), fs=256000 if mode == 'WFM' else 32000, output='sos')
        self.audio_state = np.zeros((len(self.audio_filter),2))
        self.dc_state = np.zeros(1)
        self.dc_pole = np.exp(-2*np.pi*20/(256000 if mode == 'WFM' else 32000))
        self.last = 1+0j
        self.phase = 0
        self.scale = 1.0
        self.deemph = np.zeros(1)
        self.audio_up = signal.firwin(49, 1/3) * 3
        self.audio_up_state = np.zeros(48)
        self.fft_window=np.hanning(FFT_SIZE)
        self.fft_frequencies=np.fft.fftshift(np.fft.fftfreq(FFT_SIZE,1/RATE))
        self.notches = AudioNotches(mode)
        self.blanker=ImpulseBlanker();self.reducer=SpectralReducer()
        self.nb=False;self.nr=False;self.nb_strength=50;self.nr_strength=40

    def process(self, raw, squelch):
        u = np.frombuffer(raw, np.uint8).astype(np.float32)
        x = ((u[0::2]-127.5) + 1j*(u[1::2]-127.5)) / 128
        x=self.blanker.process(x,self.nb,self.nb_strength)
        if self.mix is not None:
            x=x*self.mix*self.osc_phase
            self.osc_phase*=np.exp(2j*np.pi*self.offset*len(x)/RATE)
            self.osc_phase/=abs(self.osc_phase)
        # FFT bin amplitude is a relative dBFS display, not calibrated RF power.
        window = self.fft_window
        frames = x.reshape(-1, FFT_SIZE)
        fft = np.fft.fftshift(np.fft.fft(frames*window, axis=1), axes=1)
        power = np.mean(np.abs(fft / window.sum())**2, axis=0)
        bins = 10*np.log10(np.maximum(power,1e-12))
        if self.offset:
            frequencies=self.fft_frequencies
            bins[(frequencies<(-RATE/2+self.offset))|(frequencies>(RATE/2+self.offset))]=-120
        y, self.front_state = signal.lfilter(self.front, [1], x, zi=self.front_state)
        y = y[::4]
        y, self.channel_state = signal.lfilter(self.channel, [1], y, zi=self.channel_state)
        if self.mode != 'WFM':
            y = y[::8]
        level = float(10*np.log10(max(float(np.mean(np.abs(y)**2)), 1e-12)))
        if self.mode in ('WFM','NFM'):
            previous = np.concatenate(([self.last],y[:-1]))
            audio = np.angle(y * np.conj(previous))
            self.last = y[-1]
        elif self.mode == 'AM':
            audio = np.abs(y)
        elif self.mode == 'CW':
            phase = self.phase + 2*np.pi*700*np.arange(len(y))/32000
            audio = np.real(y*np.exp(1j*phase))
            self.phase = (self.phase + 2*np.pi*700*len(y)/32000) % (2*np.pi)
        else:
            audio = np.real(y)
        audio, self.dc_state = signal.lfilter([1,-1], [1,-self.dc_pole], audio, zi=self.dc_state)
        audio, self.audio_state = signal.sosfilt(self.audio_filter, audio, zi=self.audio_state)
        if self.mode == 'WFM':
            # 50 microsecond de-emphasis for UK/Europe broadcast FM, mono.
            a = np.exp(-1/(256000*50e-6))
            audio, self.deemph = signal.lfilter([1-a], [1,-a], audio, zi=self.deemph)
            audio = audio[::8]
        audio = self.notches.process(audio)
        rms = float(np.sqrt(np.mean(audio**2)))
        desired = min(100, .12/max(rms, .001))
        previous_scale = self.scale
        alpha = .15 if desired < self.scale else .015
        self.scale += alpha * (desired-self.scale)
        ramp = np.linspace(previous_scale,self.scale,len(audio))
        audio = .8*np.tanh(audio*ramp/.8)
        audio = self.reducer.process(audio,self.nr,self.nr_strength)
        if squelch > -100 and level < squelch:
            audio[:] = 0
        # Stateful 32 kHz -> 48 kHz interpolation avoids block-edge discontinuities.
        up = np.zeros(len(audio)*3)
        up[::3] = audio
        up, self.audio_up_state = signal.lfilter(self.audio_up, [1], up, zi=self.audio_up_state)
        audio = up[::2].astype('<f4')
        return bins.round(2).tolist(), level, audio.tobytes()

