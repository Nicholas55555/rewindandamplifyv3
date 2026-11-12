"""Reproducible explanatory animations, not recordings of laboratory hardware.

Pillow draws factual scientific schematics and probability charts. Quantum
sampling values come from the saved Qiskit output; sensing is explicitly the
instantaneous-pulse Ramsey limit. No random observations are invented.
"""
from pathlib import Path
import json
import math
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
W, H = 1200, 675
BG = '#091624'
PANEL = '#102333'
INK = '#f6f3eb'
MUTED = '#b1c0cb'
CYAN = '#64d9e9'
AMBER = '#edb568'
VIOLET = '#b9a8e5'
LINE = '#2b4253'
FONT = Path('C:/Windows/Fonts/segoeui.ttf')
BOLD = Path('C:/Windows/Fonts/segoeuib.ttf')

def font(size, bold=False):
    return ImageFont.truetype(str(BOLD if bold else FONT), size)

def text(d, xy, s, size=20, color=INK, bold=False, anchor=None):
    d.text(xy, s, font=font(size, bold), fill=color, anchor=anchor)

def rounded(d, box, fill=PANEL, outline=LINE, r=14, width=1):
    d.rounded_rectangle(box, r, fill=fill, outline=outline, width=width)

def base(kicker, title, subtitle):
    im = Image.new('RGB', (W,H), BG)
    d = ImageDraw.Draw(im)
    text(d,(48,27),'FGCU   /   REWIND & AMPLIFY',14,MUTED,True)
    text(d,(1152,27),kicker,12,CYAN,True,anchor='ra')
    d.line((48,59,1152,59),fill=LINE,width=1)
    text(d,(48,78),title,39,INK,True)
    text(d,(50,136),subtitle,17,MUTED)
    return im,d

def footer(d, text_left, text_right):
    d.line((48,617,1152,617),fill=LINE,width=1)
    text(d,(48,636),text_left,12,MUTED)
    text(d,(1152,636),text_right,12,MUTED,anchor='ra')

def sensor_frame(t):
    phase=int(t//4)%3
    offsets=[0.,5.,5.]
    df=offsets[phase]
    atom_drift=0 if phase!=2 else 5.
    p=.02+.94*.5*(1+math.exp(-.02/.2)*math.sin(2*math.pi*(df-atom_drift)*.02))
    titles=['Brightness is only one property of light.',
            'Frequency changes can hide in a steady beam.',
            'A drifting reference can hide a real change.']
    im,d=base('OPTICAL SENSING · CONCEPTUAL ANIMATION',titles[phase],
              'An atomic sensor and a coherent receiver observe frequency relative to their own references.')
    rounded(d,(48,191,370,486))
    text(d,(72,211),'LASER UNDER TEST',13,MUTED,True)
    text(d,(72,246),f'{df:+.1f} Hz',46,INK)
    text(d,(72,307),'frequency offset',15,MUTED)
    # Optical carrier is an illustration, not an optical-frequency waveform to scale.
    wave=[]
    for x in range(74,343):
        wave.append((x,377+25*math.sin((x-74)*.12-t*2.5-df*.1)))
    d.line(wave,fill=CYAN,width=3)
    text(d,(72,436),'Constant normalized power: 1.00',15,AMBER)
    # Conceptual tap branches and labelled detector paths.
    d.line((370,339,425,339),fill=CYAN,width=2)
    d.line((425,250,425,460),fill=CYAN,width=2)
    for y in [250,355,460]:
        d.line((425,y,482,y),fill=CYAN,width=2)
        q=((t*.36+y*.003)%1)
        x=425+57*q
        d.ellipse((x-4,y-4,x+4,y+4),fill=CYAN)
    rows=[(209,'Photodiode','Power / intensity','1.00',AMBER),
          (314,'Optical qubit','Frequency relative to atom',f'{p*100:.1f}% P(1)',CYAN),
          (419,'Coherent receiver','Frequency relative to stable light',f'{df:+.1f} Hz',VIOLET)]
    for y,name,sub,val,col in rows:
        rounded(d,(482,y,1152,y+83))
        d.line((503,y+19,503,y+63),fill=col,width=3)
        text(d,(521,y+13),name,21,INK,True)
        text(d,(521,y+46),sub,14,MUTED)
        text(d,(1127,y+20),val,29,col,anchor='ra')
    rounded(d,(48,522,1152,593),fill='#193b46',outline='#366270',r=10)
    takeaway=[
        'A power-only monitor cannot identify a pure frequency shift.',
        'Both phase-sensitive channels reveal it. That alone is not a quantum advantage.',
        'Here the atom shifts by the same +5 Hz. Independent references expose the ambiguity.'
    ][phase]
    text(d,(70,539),takeaway,19,INK)
    footer(d,'Illustrative Ramsey limit: 20 ms dark time, T2 = 0.2 s, readout errors 2% / 4%.',
           f'SCENE {phase+1} / 3   ·   NOT LABORATORY DATA')
    return im

def quantum_frame(t, data):
    phase=min(3,int(t//3))
    p0=data['event']['retained_model_probability']
    p1=data['event']['qiskit_amplified_probability']
    labels=['Prepare','Mark','Rewind','Amplify']
    subtitles=['Generate coherent model histories.',
               'Mark the event: a click in both time bins.',
               'Invert the model and its retained environment.',
               'Interference raises the chance of the selected event.']
    im,d=base('QUANTUM COMPUTING · IDEAL MODEL',
              'Rewind a model. Sample a rare event.',subtitles[phase])
    for i,name in enumerate(labels):
        x=48+i*281
        rounded(d,(x,190,x+261,268),fill='#193b46' if i==phase else PANEL,
                outline=CYAN if i==phase else LINE,r=10,width=2 if i==phase else 1)
        text(d,(x+17,204),f'0{i+1}',11,CYAN if i==phase else MUTED,True)
        text(d,(x+17,224),name,24,INK if i==phase else MUTED,True)
    rounded(d,(48,293,744,568))
    text(d,(72,311),'FINAL HISTORY PROBABILITIES' if phase==3 else 'REFERENCE DISTRIBUTION BEFORE AMPLIFICATION',12,MUTED,True)
    # One-round probabilities come directly from saved Qiskit, no animation
    # intermediate is presented as an additional simulated circuit result.
    key='amplified' if phase==3 else 'retained'
    colors=[MUTED,MUTED,MUTED,CYAN]
    for i,hist in enumerate(['00','01','10','11']):
        y=349+i*48
        v=data['history_probabilities'][hist][key]
        text(d,(73,y),hist,21,CYAN if hist=='11' else INK,True)
        d.rounded_rectangle((128,y+6,610,y+21),5,fill=LINE)
        width=max(1,482*v)
        d.rounded_rectangle((128,y+6,128+width,y+21),4,fill=colors[i])
        text(d,(716,y),f'{100*v:.3f}%',18,CYAN if hist=='11' else MUTED,anchor='ra')
        if hist=='11' and phase==1:
            text(d,(580,y-17),'PHASE MARKED',10,AMBER,anchor='ra')
    text(d,(72,549),'Before/final comparison. Intermediate circuit states are not plotted.',12,MUTED)
    rounded(d,(768,293,1152,568))
    text(d,(792,313),'SELECTED EVENT',12,MUTED,True)
    p=p1 if phase==3 else p0
    text(d,(792,347),f'{100*p:.4f}%',54,CYAN)
    text(d,(792,424),'one ideal round' if phase==3 else 'before amplification',18,INK)
    text(d,(792,468),f'{p1/p0:.2f}× event probability',22,AMBER,True)
    text(d,(792,507),'11 qubits · 6,663 generic CX',15,MUTED)
    text(d,(792,532),'Saved Qiskit statevector experiment',12,MUTED)
    footer(d,'The inverse reverses a model circuit, not a detected photon, a laser or a wafer.',
           'COARSE TWO-BIN MODEL · NO HARDWARE NOISE')
    return im

def save_gif(name, frames, duration):
    # A global palette avoids palette flicker between adjacent frames.
    palette=frames[0].quantize(colors=128,method=Image.Quantize.MEDIANCUT)
    pal=[im.quantize(palette=palette,dither=Image.Dither.NONE) for im in frames]
    pal[0].save(HERE/f'{name}.gif',save_all=True,append_images=pal[1:],duration=duration,
                loop=0,optimize=True,disposal=2)

def main():
    HERE.mkdir(exist_ok=True)
    data=json.loads((ROOT/'qrsm_photon_poc/generated/two_bin_double.json').read_text())
    sensing=[sensor_frame(i/10) for i in range(120)]
    save_gif('laser-diagnostic-lenses',sensing,100)
    sensing[50].save(HERE/'laser-diagnostic-lenses.png')
    quantum=[quantum_frame(i/4,data) for i in range(48)]
    save_gif('rewind-amplify',quantum,250)
    quantum[40].save(HERE/'rewind-amplify.png')
    meta={'dimensions':[W,H],'duration_seconds':12,'sensor':{'type':'analytical explanatory schematic','tau_seconds':.02,'T2_seconds':.2,'readout_0_to_1':.02,'readout_1_to_0':.04,'scenes':'zero detuning; +5 Hz source; +5 Hz source plus +5 Hz atomic reference'},'quantum':{'type':'saved ideal Qiskit result schematic','source':'qrsm_photon_poc/generated/two_bin_double.json','p_before':data['event']['retained_model_probability'],'p_after':data['event']['qiskit_amplified_probability']},'note':'Animation is explanatory, not a laboratory or physical device recording.'}
    (HERE/'animation_manifest.json').write_text(json.dumps(meta,indent=2)+'\n')
    print(json.dumps({p.name:p.stat().st_size for p in HERE.glob('*.gif')},indent=2))

if __name__=='__main__':
    main()
