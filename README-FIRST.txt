HamTech RTL Comander V16 - RTL-SDR Blog V4
======================================

V16 READABLE DROPDOWNS
Every dropdown and its option list now uses black text on a light
background, including MODE, FILTER, STEP, SPAN, WF SPAN and DX band.
This stays readable with any selected colour theme.

V15 RX MARKERS, DX OVERLAY AND WATERFALL SPAN
Yellow RX lines mark the tuned frequency on spectrum and waterfall.
Faint shading shows the selected receive filter; LSB/USB show its side.
WF SPAN selects an independent 10 kHz–1.024 MHz view, or FOLLOW SPECTRUM.
Spectrum SPAN also gains 10 kHz, 25 kHz and 500 kHz options. Clicking
each display tunes using its own span. Changing waterfall span clears
its old history. The frequency readout size remains unchanged.
DX ON overlays in-range HamQTH callsigns on the waterfall, with 30 second
refresh while enabled. Click a label to tune; hover shows report time.
Markers/labels are drawn on a separate canvas, never burned into history.
DX reports can be delayed; this is not proof a station is currently active.
WF GAIN now ranges from -60 to +60; positive gain also lowers the signal
contrast gate from 8 toward 6 dB, so weaker peaks can show yellow/red.
The estimated noise floor itself stays blue. High gain can reveal noise
peaks as well as weak signals. This adjusts display sensitivity, not RF gain.

V14 FREQUENCY STEP INDICATOR
A small yellow STEP box sits inside the frequency panel above the digits.
It shows the current tuning step in Hz/kHz. Click it to cycle steps.
It stays synced with the dropdown, right-side STEP button and UK presets.
Frequency readout dimensions and font fitting are unchanged.

V13 FREQUENCY DISPLAY AND UK PRESETS
The main frequency fills its black panel and automatically scales to fit
HF/VHF/UHF values. Mouse-wheel tuning and click-to-edit still work. The
unused TX square is removed; VFO swap and RX ONLY remain.
MARINE UK tunes channel 16 (156.800 MHz), selects FM/NFM, 16 kHz filter
and 25 kHz tuning step, and opens a common voice-channel chooser.
Channel 80 includes separate ship (157.025) and shore (161.625 MHz) presets.
PMR UK tunes analogue channel 1 (446.006250 MHz), selects FM/NFM, 12.5 kHz
filter and step, and offers channels 1–16 through 446.193750 MHz.
This is an analogue receiver; digital voice and CTCSS/DCS are not decoded.

V12 SIGNAL-ONLY WATERFALL COLOURS
The waterfall now measures the median noise level in the visible span.
The background stays blue as RF/noise levels change. Light yellow only
appears for bins above that floor (12 dB at WF GAIN 0); stronger signals
progress to orange/red. WF GAIN adjusts signal colour sensitivity, but
V15 uses a 6–8 dB contrast gate so the noise floor stays blue at high gain.
A median estimate can be affected by signals occupying most of the span;
choose a wider span if a broad signal fills the entire display.
These are relative signal/noise colours, not calibrated RF measurements.

V11 FINER SPECTRUM / WATERFALL
The display now uses 8192 FFT bins at 125 Hz spacing across 1.024 MHz,
compared with the previous 1024 transmitted points at 1000 Hz spacing.
Both canvases are 2000 pixels wide internally; the waterfall has 360
vertical pixels for finer history rows. Narrow spans use interpolation
and wide spans preserve bin peaks so narrow signals are not skipped.
The physical sample rate and audio processing are unchanged.
Waterfall colours: dark navy/blue background, yellow for medium signals,
orange then red for strong signals. WF GAIN shifts the colour thresholds.
V12 replaces those fixed colour levels with the noise-relative mapping above.
Relative display levels are not calibrated signal strength measurements.

V10 NB / NR AND COLOURS
NB and NR now toggle on/off in the top row and start OFF. MENU / gear
has strength sliders, saved locally. NB detects and interpolates short
I/Q amplitude spikes before demodulation; increasing strength lowers the
threshold and widens the blanking region. It bypasses dense overload
rather than blanking the whole block. NR is a spectral audio denoiser
with continuous overlap-add, smooth gain transitions and an 8ms delay
on both dry and filtered paths. Strong settings may soften wanted audio.
NB/NR are distinct from ANF (tone suppression) and the manual notch.
Colours: MENU has rainbow swatches plus custom Background, Panel tint
and Borders/glow pickers. Swatches apply matching dark surrounds and
coloured borders. Choices persist locally; RESET COLOURS restores blue.
Active controls stay green, spectrum stays black/green, waterfall stays blue.

V9 FILTERS AND DISPLAY
ANF automatically suppresses one strong persistent narrow audio tone in
LSB/USB/AM/NFM. It is bypassed in CW and WFM to preserve wanted tones/music.
It is a conservative tone notch, not general noise reduction; turn it off
if it affects a wanted signal. NOTCH enables a manual audio notch. MENU
sets centre frequency (100–12000 Hz) and width (20–500 Hz). Default 1000/80 Hz.
Filter enable/disable and centre changes blend smoothly across an audio block.
PRE requests up to +10 dB of tuner gain from the RF gain setting; ATT
requests up to -20 dB. They are mutually exclusive, select manual gain,
and are limited to the actual tuner gain steps (0–49.6 dB). RF GAIN now
shows effective requested dB or AUTO. Turning a preset off restores base gain.
They do not switch a separate physical preamp, attenuator or bias tee.
Turning tuner AGC on clears PRE/ATT. RF +/- adjusts the base setting.
The waterfall uses dark navy/blue, with pale highlights for strong signals.
The spectrum has a black background and green trace. REF changes the top
display level, RANGE changes vertical dB span, and AVG smooths the trace.
Existing spectrum SPAN changes horizontal bandwidth. Spectrum controls
are saved locally and do not alter audio or RF settings.

V8 AIRBAND
New left-side AIRBAND button: 118–137 MHz, AM. Clicking it tunes to
118.000000 MHz and selects AM. Use the wheel, STEP/arrows or frequency
entry to tune the required frequency within this range.

V7 CONTROLS
STEP cycles 100 Hz, 10 Hz, 1 kHz, 5 kHz and 12.5 kHz; the dropdown also works.
Hover the main frequency and scroll: up increases, down decreases by STEP.
Click the main frequency to select all, type MHz (7.100000) or grouped Hz
(7.100.000), then press Enter. Escape cancels an edit. Arrow keys also tune.
WF GAIN changes display sensitivity from -60 to +60; saved locally. It
does not change RF or audio gain. Gain changes clear previous waterfall rows.
DX CLUSTER fetches HamQTH spots via the local Python server, refreshes every
30 seconds while open, and offers a band filter and click-to-tune frequencies.
Current reception mode is retained: choose CW/LSB/USB as appropriate. Digital
spots require a separate decoder. No account or spot posting is involved.
The date/time of each report is visible; upstream feeds may be delayed.
If the feed is unavailable, the dialog reports this and retains previous rows.

V6 CAPTURE CHANGE
The video showed regular sound/silence periods. V5 still serialized synchronous
USB reads with DSP processing, which can deliver less PCM than playback needs.
V6 uses rtlsdr_read_async with 16 pending USB transfers, copying sample blocks
into a queue. A separate thread runs DSP. USB acquisition stays active while
DSP works. Tuning does not reset active asynchronous USB transfers.
SYSTEM STATUS reports PCM production (target about 48000 samples/second), USB
queue depth and USB drops. After 10 seconds, report these values with audio gaps
and skips if chuffing remains. A persistently low PCM rate means starvation;
an increasing USB queue/drop count points to processing falling behind.
A continuously growing gap count with normal PCM rate points to playback or
network/scheduling delays. These are diagnostic clues, not hardware proof.
Capture timing, transport/DSP and audio worklet software tests passed. In the
capture test, 20ms DSP delays did not delay the continuous USB callback stream.
Your physical dongle and Windows audio still require a live test.

YOUR DLLS ARE INCLUDED
rtlsdr.dll, msvcr100.dll and pthreadVC2.dll are copied byte-for-byte from your
uploaded working files. You do not need to add them again or run the installer.
The rtlsdr.dll file is 64-bit and contains Blog V4 support. It also imports the
Microsoft VCRUNTIME140 runtime. Your working laptop probably already has it;
if DLL loading fails, check the Microsoft Visual C++ x64 runtime installation.
The uploaded msvcr100.dll is a different runtime and is preserved as supplied.
Python 3.10+ 64-bit, the existing WinUSB driver, and Python dependencies are still
required. This ZIP does not include a Python interpreter or OS driver installer.

START
1. Stop the previous Python receiver window and close any SDR software using USB.
2. Extract this whole ZIP into a NEW folder. Do not launch inside the ZIP.
3. Run START-HAMTEC-DIRECT-USB-AUDIO.bat. First run installs Python dependencies
   into a local .venv folder; it requires internet access for that step.
4. Browser: http://127.0.0.1:8765 . Use Edge or Chrome. Press POWER for audio.
   If you see an older page, use Ctrl+F5. Keep the Python window open.

WFM
There is a WFM button in the bottom MODE row as well as a WFM dropdown selection.
Use WFM for broadcast FM, select 180 kHz bandwidth, and tune a known strong local
FM station. FM/NFM is narrow FM for voice communications; it is not broadcast FM.
WFM is mono with 50 microsecond de-emphasis for UK/Europe, without stereo/RDS.

CHUFFING AUDIO
Playback now runs in a dedicated AudioWorklet with a 180ms startup/jitter buffer,
resampling for the actual audio device clock, and gentle clock-rate correction.
It no longer starts/stops a separate AudioBufferSource for each USB chunk.
Audio gain changes are smoothed across samples to reduce block-edge pumping,
and limiting is soft instead of abrupt clipping. This targets buffer gaps and
block-edge discontinuities; interference or overload can still cause noise.
SYSTEM STATUS shows buffer size, gaps, skips and audio RMS. TEST SPEAKERS checks
Windows/browser output separately from reception. Record those counters if the
problem remains; distinguish an actual RF signal from an audio queue problem.

HF / V4
The driver automatically handles the V4's HF upconversion. This console uses
normal tuner mode and does NOT enable V3 Q-branch direct sampling or add a
manual 28.8MHz conversion offset.
The startup terminal and SYSTEM STATUS now report USB manufacturer/product,
V4 model recognition, tuner type and the loaded DLL path. Both frequency and
sample rate are read back from the driver. Expected sample rate: 1.024 MS/s.
A 128kHz LO offset moves the selected channel away from the RTL's centre DC spur;
DSP cancels that offset so you enter the actual desired reception frequency.
At the top tuning limit the offset is reversed. This is unrelated to the V4's
internal HF upconverter. Wrapped FFT bins at the full spectrum edge are blanked.
40m starts at 7.100000 MHz / LSB; 20m at 14.200000 MHz / USB. These are presets,
not guaranteed active stations. Use a suitable HF antenna and a known active
signal when testing. Squelch starts OFF (-100 dBFS). Increase RF gain if needed.
V4 recognition NO means the driver did not identify the expected EEPROM model;
HF support cannot then be assumed. Check the official software/model details;
this program never writes EEPROM or changes your dongle identity.

DRIVER DIAGNOSTICS
A V4-capable DLL is necessary but cannot prove the connected dongle was detected
correctly. No simulated 'HF OK' status is shown. Driver errors are displayed and
reported in the terminal. If there is no live spectrum, inspect the terminal.
Do not change a working WinUSB setup merely to use this ZIP.

Validation: four Python tests passed for USB sample streaming, squelch/sideband
filtering, digital-offset reception and WFM demodulation. Worklet tests passed
at 48kHz and 44.1kHz, including a 120ms delivery stall, continuous tone playback
and mute. Physical USB HF reception and Windows audio remain laptop tests.

Sources:
https://www.rtl-sdr.com/v4/
https://github.com/rtlsdrblog/rtl-sdr-blog
https://developer.mozilla.org/en-US/docs/Web/API/AudioWorkletProcessor

DX source: https://www.hamqth.com/dxc_csv.php

UK preset references:
https://www.gov.uk/government/publications/mgn-324-mf-amendment-2-navigation-watchkeeping-safety-use-of-very-high-frequency-vhf-radio-and-automatic-identification-system-ais/mgn-324-mf-amendment-2
https://www.navcen.uscg.gov/international-vhf-marine-radio-channels-freq
https://portal.etsi.org/webapp/WorkProgram/Report_WorkItem.asp?WKI_ID=47876
