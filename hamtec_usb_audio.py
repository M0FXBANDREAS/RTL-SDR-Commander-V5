"""HamTec direct USB receiver: fresh I/Q -> stateful DSP -> queued PCM."""
import argparse
import asyncio
import contextlib
import ctypes as C
import json
import os
from pathlib import Path
import queue
import threading
import time
import webbrowser

from aiohttp import web, WSMsgType
from dx_cluster import install_dx_routes
from dsp import DSP, RATE, BLOCK
LO_OFFSET=128000
RX_CALLBACK=C.CFUNCTYPE(None,C.POINTER(C.c_ubyte),C.c_uint32,C.c_void_p)

HERE = Path(__file__).resolve().parent
GAINS = [0,9,14,27,37,77,87,125,144,157,166,197,207,229,254,280,297,328,338,364,372,386,402,421,434,439,445,480,496]
CONFIG = web.AppKey('config',dict)

def validate(value):
    if not isinstance(value,dict): raise ValueError('Invalid controls')
    s=dict(freq=int(value.get('freq',4006934)),mode=value.get('mode','LSB'),bandwidth=int(value.get('bandwidth',2400)),gain=int(value.get('gain',372)),agc=bool(value.get('agc',True)),squelch=float(value.get('squelch',-100)),ppm=int(value.get('ppm',0)),anf=bool(value.get('anf',False)),notch=bool(value.get('notch',False)),notch_hz=int(value.get('notch_hz',1000)),notch_width=int(value.get('notch_width',80)),nb=bool(value.get('nb',False)),nr=bool(value.get('nr',False)),nb_strength=int(value.get('nb_strength',50)),nr_strength=int(value.get('nr_strength',40)))
    limits={'LSB':(1800,3000),'USB':(1800,3000),'CW':(250,1000),'AM':(5000,12000),'NFM':(8000,25000),'WFM':(150000,200000)}
    if s['mode'] not in limits or not 500000<=s['freq']<=1766000000 or s['gain'] not in GAINS or not -100<=s['squelch']<=-20 or not -200<=s['ppm']<=200: raise ValueError('Control outside receiver range')
    if not 100<=s['notch_hz']<=12000 or not 20<=s['notch_width']<=500:raise ValueError('Notch settings outside range')
    if not 0<=s['nb_strength']<=100 or not 0<=s['nr_strength']<=100:raise ValueError('Noise strength outside range')
    lo,hi=limits[s['mode']]
    if not lo<=s['bandwidth']<=hi: raise ValueError('Filter incompatible with mode')
    return s

class USB:
    def __init__(self):
        self.streaming=False
        self.samples=queue.Queue(maxsize=64)
        self.capture_error=None
        self.capture_count=0
        self.capture_drops=0
        self.capture_started=0.0
        self.capture_thread=None
        self.dll_dirs=[]
        if os.name=='nt':
            if C.sizeof(C.c_void_p)!=8: raise RuntimeError('Install 64-bit Python for the x64 driver.')
            for folder in [HERE,HERE/'RTL'/'x64']:
                if folder.is_dir(): self.dll_dirs.append(os.add_dll_directory(str(folder)))
        dll=HERE/'rtlsdr.dll'
        if not dll.exists(): dll=HERE/'RTL'/'x64'/'rtlsdr.dll'
        if not dll.exists(): raise RuntimeError('Missing rtlsdr.dll. Copy the official V4 x64 DLLs to RTL/x64 and run INSTALL-RTL-V4-FILES.bat.')
        print('Loading RTL-SDR driver:',dll)
        try: self.r=C.CDLL(str(dll))
        except OSError as e: raise RuntimeError('Cannot load rtlsdr.dll. Copy ALL accompanying x64 DLLs; check 64-bit Python.') from e
        signatures={'rtlsdr_get_usb_strings':([C.c_void_p,C.c_char_p,C.c_char_p,C.c_char_p],C.c_int),'rtlsdr_check_dongle_model':([C.c_void_p,C.c_char_p,C.c_char_p],C.c_int),'rtlsdr_get_tuner_type':([C.c_void_p],C.c_int),'rtlsdr_get_center_freq':([C.c_void_p],C.c_uint32),'rtlsdr_get_sample_rate':([C.c_void_p],C.c_uint32),'rtlsdr_get_direct_sampling':([C.c_void_p],C.c_int),'rtlsdr_get_device_count':([],C.c_uint32),'rtlsdr_open':([C.POINTER(C.c_void_p),C.c_uint32],C.c_int),'rtlsdr_close':([C.c_void_p],C.c_int),'rtlsdr_set_sample_rate':([C.c_void_p,C.c_uint32],C.c_int),'rtlsdr_set_center_freq':([C.c_void_p,C.c_uint32],C.c_int),'rtlsdr_set_tuner_gain_mode':([C.c_void_p,C.c_int],C.c_int),'rtlsdr_set_tuner_gain':([C.c_void_p,C.c_int],C.c_int),'rtlsdr_set_freq_correction':([C.c_void_p,C.c_int],C.c_int),'rtlsdr_set_agc_mode':([C.c_void_p,C.c_int],C.c_int),'rtlsdr_set_direct_sampling':([C.c_void_p,C.c_int],C.c_int),'rtlsdr_reset_buffer':([C.c_void_p],C.c_int),'rtlsdr_read_async':([C.c_void_p,RX_CALLBACK,C.c_void_p,C.c_uint32,C.c_uint32],C.c_int),'rtlsdr_cancel_async':([C.c_void_p],C.c_int)}
        for name,(args,result) in signatures.items():
            fn=getattr(self.r,name);fn.argtypes=args;fn.restype=result
        if self.r.rtlsdr_get_device_count()<1: raise RuntimeError('No RTL-SDR detected. Check WinUSB; close SDR#, rtl_test and rtl_tcp.')
        self.dev=C.c_void_p()
        if self.r.rtlsdr_open(C.byref(self.dev),0): raise RuntimeError('USB device busy or inaccessible. Close other SDR software.')
        try:
            self.check(self.r.rtlsdr_set_sample_rate(self.dev,RATE),'sample rate')
            if self.r.rtlsdr_get_direct_sampling(self.dev)!=0:
                self.check(self.r.rtlsdr_set_direct_sampling(self.dev,0),'normal V4 tuner mode')
            manufacturer,product,serial=(C.create_string_buffer(256) for _ in range(3))
            self.check(self.r.rtlsdr_get_usb_strings(self.dev,manufacturer,product,serial),'USB identity')
            v4=bool(self.r.rtlsdr_check_dongle_model(self.dev,b'RTLSDRBlog',b'Blog V4'))
            tuner=self.r.rtlsdr_get_tuner_type(self.dev)
            self.info=dict(v4=v4,tuner=tuner,manufacturer=manufacturer.value.decode(errors='replace'),product=product.value.decode(errors='replace'))
            self.info['summary']=f"{self.info['manufacturer']} / {self.info['product']} | V4 recognition: {'YES' if v4 else 'NO'} | tuner: {tuner} | normal sampling | digital LO offset 128 kHz"
            print(self.info['summary'])
            if not v4: print('WARNING: Blog V4 identity not recognized. HF auto-upconversion may not be active; check model/EEPROM with official software.')
            self.check(self.r.rtlsdr_set_agc_mode(self.dev,0),'digital AGC')
            self.previous=None
            self.apply(validate({}))
            self.r.rtlsdr_reset_buffer(self.dev)
        except Exception:
            self.close();raise
        if self.r.rtlsdr_get_sample_rate(self.dev)!=RATE: raise RuntimeError('Driver sample rate does not match the audio pipeline.')
        self.buf=(C.c_ubyte*(BLOCK*2))()
    @staticmethod
    def check(code,label):
        if code: raise RuntimeError(f'Driver rejected {label} (code {code}).')
    def apply(self,s):
        old=self.previous or {}
        if s['freq']!=old.get('freq'):
            self.offset=LO_OFFSET if s['freq']+LO_OFFSET<=1766000000 else -LO_OFFSET
            expected=s['freq']+self.offset
            self.check(self.r.rtlsdr_set_center_freq(self.dev,expected),'frequency')
            if self.r.rtlsdr_get_center_freq(self.dev)!=expected: raise RuntimeError('Driver frequency read-back differs from requested frequency.')
            if not self.streaming:self.check(self.r.rtlsdr_reset_buffer(self.dev),'buffer reset')
        if s['agc']!=old.get('agc'): self.check(self.r.rtlsdr_set_tuner_gain_mode(self.dev,0 if s['agc'] else 1),'tuner AGC')
        if not s['agc'] and (s['gain']!=old.get('gain') or old.get('agc')): self.check(self.r.rtlsdr_set_tuner_gain(self.dev,s['gain']),'RF gain')
        if s['ppm']!=old.get('ppm',0): self.check(self.r.rtlsdr_set_freq_correction(self.dev,s['ppm']),'PPM correction')
        self.previous=s.copy()
    def start_capture(self):
        if self.streaming:return
        # rtlsdr_read_async maintains multiple USB transfers continuously, while DSP
        # consumes copied blocks independently. Keep the callback alive until joined.
        self.streaming=True
        self.capture_error=None
        self.capture_count=0
        self.capture_started=time.monotonic()
        def callback(buf,length,ctx):
            if not self.streaming:return
            if length != BLOCK*2:
                self.capture_error=f'Unexpected USB block size {length}'
                return
            raw=C.string_at(buf,length)
            self.capture_count+=1
            try:self.samples.put_nowait(raw)
            except queue.Full:
                try:self.samples.get_nowait()
                except queue.Empty:pass
                self.capture_drops+=1
                try:self.samples.put_nowait(raw)
                except queue.Full:pass
        self.callback=RX_CALLBACK(callback)
        def capture():
            result=self.r.rtlsdr_read_async(self.dev,self.callback,None,16,BLOCK*2)
            if self.streaming:self.capture_error=f'Continuous USB capture stopped (code {result}).'
        self.capture_thread=threading.Thread(target=capture,daemon=True,name='RTL-USB-capture')
        self.capture_thread.start()
    def read(self):
        if not self.streaming:self.start_capture()
        if self.capture_error:raise RuntimeError(self.capture_error)
        try:return self.samples.get(timeout=5)
        except queue.Empty:raise RuntimeError(self.capture_error or 'Continuous USB capture produced no samples for 5 seconds.')
    def stop_capture(self):
        if not self.streaming and not (self.capture_thread and self.capture_thread.is_alive()):return
        self.streaming=False
        # The library initializes asynchronous state within the capture thread.
        # Retry cancellation briefly if a client disconnects during startup.
        for _ in range(20):
            self.r.rtlsdr_cancel_async(self.dev)
            if self.capture_thread:
                self.capture_thread.join(.1)
                if not self.capture_thread.is_alive():break
        if self.capture_thread and self.capture_thread.is_alive():
            raise RuntimeError('USB capture is still active; restart the receiver before reconnecting.')
        while not self.samples.empty():
            try:self.samples.get_nowait()
            except queue.Empty:break
    def close(self):
        if self.dev:
            self.stop_capture()
            self.r.rtlsdr_close(self.dev);self.dev=None

async def socket(request):
    cfg=request.app[CONFIG]
    if request.host not in {f'127.0.0.1:{cfg["port"]}',f'localhost:{cfg["port"]}'} or request.headers.get('Origin',f'http://{request.host}')!=f'http://{request.host}': raise web.HTTPForbidden()
    if cfg['active']: raise web.HTTPConflict(text='Only one receiver tab at a time')
    cfg['active']=True
    ws=web.WebSocketResponse(heartbeat=20,max_msg_size=4096)
    await ws.prepare(request)
    frames=asyncio.Queue(maxsize=8);controls=queue.Queue();stop=threading.Event();loop=asyncio.get_running_loop()
    def publish(item):
        if stop.is_set():return
        if frames.full():frames.get_nowait()
        frames.put_nowait(item)
    def worker():
        try:
            state=validate({});cfg['device'].apply(state);
            if hasattr(cfg['device'],'start_capture'):cfg['device'].start_capture()
            started=time.monotonic();dsp=DSP(state['mode'],state['bandwidth'],getattr(cfg['device'],'offset',0));seq=0
            while not stop.is_set():
                next_state=None
                while not controls.empty(): next_state=controls.get_nowait()
                if next_state:
                    cfg['device'].apply(next_state)
                    if (state['mode'],state['bandwidth'],state['freq'])!=(next_state['mode'],next_state['bandwidth'],next_state['freq']):dsp=DSP(next_state['mode'],next_state['bandwidth'],getattr(cfg['device'],'offset',0))
                    state=next_state
                raw=cfg['device'].read()
                dsp.nb=state['nb'];dsp.nr=state['nr'];dsp.nb_strength=state['nb_strength'];dsp.nr_strength=state['nr_strength']
                dsp.notches.configure(state['anf'],state['notch'],state['notch_hz'],state['notch_width'])
                bins,level,pcm=dsp.process(raw,state['squelch'])
                seq+=1
                loop.call_soon_threadsafe(publish,dict(bins=bins,level=level,pcm=pcm,seq=seq,freq=state['freq'],audio_rate=seq*1536/max(.001,time.monotonic()-started),capture_drops=getattr(cfg['device'],'capture_drops',0),usb_queue=getattr(cfg['device'],'samples',queue.Queue()).qsize()))
        except Exception as e:
            if not stop.is_set():loop.call_soon_threadsafe(publish,dict(error=str(e)))
        finally:
            if hasattr(cfg['device'],'stop_capture'):
                try:cfg['device'].stop_capture()
                except Exception as e:print('USB capture shutdown:',e)
    thread=threading.Thread(target=worker,daemon=True);thread.start()
    await ws.send_json(dict(type='connected',rate=RATE,freq=4006934,device=getattr(cfg['device'],'info',{})))
    async def stream():
        while not ws.closed:
            try:item=await asyncio.wait_for(frames.get(),5)
            except asyncio.TimeoutError:
                await ws.send_json(dict(type='error',message='No fresh USB samples for 5 seconds. Check the receiver.'));await ws.close();return
            if 'error' in item:
                await ws.send_json(dict(type='error',message=item['error']));await ws.close();return
            if item['seq']%2==0:await ws.send_json(dict(type='spectrum',bins=item['bins'],level=item['level'],seq=item['seq'],freq=item['freq'],audio_rate=item['audio_rate'],capture_drops=item['capture_drops'],usb_queue=item['usb_queue']))
            await ws.send_bytes(item['pcm'])
    task=asyncio.create_task(stream())
    try:
        async for msg in ws:
            if msg.type==WSMsgType.TEXT:
                try:controls.put(validate(json.loads(msg.data)))
                except (ValueError,TypeError,OverflowError):await ws.send_json(dict(type='error',message='Invalid receiver settings'))
    finally:
        stop.set();task.cancel()
        with contextlib.suppress(asyncio.CancelledError,ConnectionError):await task
        await asyncio.to_thread(thread.join,8)
        # Do not allow a second USB reader if a driver read remains stuck.
        capture_thread=getattr(cfg['device'],'capture_thread',None)
        cfg['active']=thread.is_alive() or bool(capture_thread and capture_thread.is_alive())
        await ws.close()
    return ws

def create_app(device,port=8765):
    app=web.Application();app[CONFIG]=dict(device=device,port=port,active=False)
    app.router.add_get('/ws',socket)
    install_dx_routes(app,port)
    async def index(request): return web.FileResponse(HERE/'console.html')
    async def asset(request): return web.FileResponse(HERE/request.match_info['name'])
    app.router.add_get('/',index)
    app.router.add_get(r'/{name:console\.js|console\.css|audio-player\.js|pcm-worklet\.js}',asset)
    return app

if __name__=='__main__':
    try:device=USB()
    except Exception as e:raise SystemExit(str(e))
    print('HamTech V17: asynchronous USB capture + independent DSP + 48 kHz audio')
    print('Open http://127.0.0.1:8765 . Press POWER to enable audio.')
    app=create_app(device)
    async def open_browser(app):asyncio.get_running_loop().call_later(1,webbrowser.open,'http://127.0.0.1:8765')
    app.on_startup.append(open_browser)
    try:web.run_app(app,host='127.0.0.1',port=8765)
    finally:device.close()
