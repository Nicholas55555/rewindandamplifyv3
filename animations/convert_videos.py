"""Convert the two original explanatory GIFs into browser-compatible MP4.

No scientific frames or values are regenerated. GIF frame durations are kept,
with repeated frames on a20fps timeline. H.264 requires even dimensions for
yuv420p, so one background pixel row is added at the bottom (no crop/scale).
Every output frame is decoded and compared with its timed source GIF frame.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import re
import shutil
import struct
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont


HERE=Path(__file__).resolve().parent
FPS=20
SPECS=[
    {'stem':'laser-diagnostic-lenses','scene_times':[2.,6.,10.],
     'scene_labels':['Reference source','Source shifts +5Hz','Atomic reference also shifts +5Hz']},
    {'stem':'rewind-amplify','scene_times':[1.5,4.5,7.5,10.5],
     'scene_labels':['Prepare','Mark','Rewind','Amplify']},
]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ffmpeg_path(explicit=None):
    if explicit:return str(Path(explicit).resolve())
    executable=shutil.which('ffmpeg')
    if executable:return executable
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError as exc:
        raise RuntimeError('Install imageio-ffmpeg, place ffmpeg on PATH, or pass --ffmpeg.') from exc


def source_info(path):
    with Image.open(path) as image:
        dimensions=list(image.size)
        durations=[]
        for i in range(image.n_frames):
            image.seek(i)
            duration=image.info.get('duration',0)
            if duration<=0:raise ValueError(f'Nonpositive GIF duration in {path.name}, frame{i}')
            durations.append(duration)
    return {'width':dimensions[0],'height':dimensions[1],
            'frame_count':len(durations),'frame_durations_ms':durations,
            'duration_seconds':sum(durations)/1000,'sha256':sha256(path)}


def mp4_boxes(path):
    boxes=[]
    with path.open('rb') as file:
        total=path.stat().st_size
        while file.tell()<total:
            offset=file.tell();head=file.read(8)
            if len(head)!=8:raise ValueError('Truncated MP4 box header')
            size,kind=struct.unpack('>I4s',head)
            if size==1:size=struct.unpack('>Q',file.read(8))[0]
            elif size==0:size=total-offset
            if size<8 or offset+size>total:raise ValueError('Invalid MP4 box size')
            boxes.append({'type':kind.decode('ascii','replace'),'offset':offset,'size':size})
            file.seek(offset+size)
    return boxes


def inspect_video(ffmpeg,path):
    # An input-only invocation reports container/stream metadata and exits1
    # because no output was requested. Decoding is checked separately below.
    info=subprocess.run([ffmpeg,'-hide_banner','-i',str(path)],
                        capture_output=True,text=True,encoding='utf8',errors='replace')
    stderr=info.stderr
    duration=re.search(r'Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)',stderr)
    stream=next((line for line in stderr.splitlines() if 'Video:' in line),'')
    size=re.search(r'\b(\d{3,})x(\d{3,})\b',stream)
    rate=re.search(r'([0-9.]+) fps',stream)
    if not duration or not size or not rate:raise ValueError('Could not inspect video metadata: '+stderr)
    seconds=3600*int(duration[1])+60*int(duration[2])+float(duration[3])
    boxes=mp4_boxes(path)
    offsets={b['type']:b['offset'] for b in boxes}
    return {'codec':'h264' if 'Video: h264' in stream else stream,
            'codec_profile':'Constrained Baseline' if 'Constrained Baseline' in stream else 'other',
            'codec_tag':'avc1' if '(avc1 /' in stream else 'other',
            'pixel_format':'yuv420p' if 'yuv420p' in stream else 'other',
            'width':int(size[1]),'height':int(size[2]),'frame_rate':float(rate[1]),
            'duration_seconds':seconds,'audio':bool(re.search(r'Stream.*Audio:',stderr)),
            'faststart':'moov' in offsets and 'mdat' in offsets and offsets['moov']<offsets['mdat'],
            'top_level_boxes':boxes,'stream_description':stream.strip()}


def read_exact(pipe,size):
    chunks=[];remaining=size
    while remaining:
        block=pipe.read(remaining)
        if not block:
            if remaining==size:return None
            raise ValueError('Decoded video ended in a partial frame')
        chunks.append(block);remaining-=len(block)
    return b''.join(chunks)


def validate(ffmpeg,path,gif,spec,source):
    info=inspect_video(ffmpeg,path)
    assert info['codec']=='h264' and info['codec_tag']=='avc1'
    assert info['pixel_format']=='yuv420p' and not info['audio'] and info['faststart']
    assert (info['width'],info['height'])==(source['width'],source['height']+1)==(1200,676)
    assert info['frame_rate']==FPS and abs(info['duration_seconds']-12.)<.001
    expected_count=round(source['duration_seconds']*FPS)
    scene_indices={round(t*FPS):(t,label) for t,label in zip(spec['scene_times'],spec['scene_labels'])}
    ends=np.cumsum(source['frame_durations_ms'])/1000
    command=[ffmpeg,'-hide_banner','-loglevel','error','-nostdin','-i',str(path),
             '-map','0:v:0','-an','-f','rawvideo','-pix_fmt','rgb24','pipe:1']
    decoder=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    count=0;maes=[];mses=[];scene_checks=[];thumbnails=[]
    validation_dir=HERE/'video-validation';validation_dir.mkdir(exist_ok=True)
    last_source_index=-1
    try:
        with Image.open(gif) as original:
            while True:
                raw=read_exact(decoder.stdout,info['width']*info['height']*3)
                if raw is None:break
                actual=np.frombuffer(raw,np.uint8).reshape(info['height'],info['width'],3)
                t=count/FPS
                source_index=min(int(np.searchsorted(ends,t+1e-8,side='right')),len(ends)-1)
                if source_index!=last_source_index:
                    original.seek(source_index)
                    expected=np.asarray(original.convert('RGB'),dtype=np.int16)
                    last_source_index=source_index
                diff=actual[:source['height']].astype(np.int16)-expected
                mae=float(np.mean(np.abs(diff)))
                mse=float(np.mean(diff.astype(np.float32)**2))
                maes.append(mae);mses.append(mse)
                if count in scene_indices:
                    ts,label=scene_indices[count]
                    image=Image.fromarray(actual.copy())
                    png=validation_dir/f'{spec["stem"]}-scene-{len(scene_checks)+1}.png'
                    image.save(png)
                    scene_checks.append({'time_seconds':ts,'label':label,'video_frame':count,
                                         'source_gif_frame':source_index,
                                         'decoded_png':str(png.relative_to(HERE)).replace('\\','/'),
                                         'mean_absolute_rgb_error':mae,
                                         'psnr_db':10*math.log10(255**2/max(mse,1e-15)),
                                         'decoded_rgb_sha256':hashlib.sha256(raw).hexdigest()})
                    thumbnails.append((label,image.copy()))
                count+=1
    finally:
        decoder.stdout.close()
    error=decoder.stderr.read().decode('utf8','replace');returncode=decoder.wait()
    if returncode or error.strip():raise RuntimeError('Full-frame decode failed: '+error)
    assert count==expected_count==240,(count,expected_count)
    assert len(scene_checks)==len(scene_indices)
    assert max(maes)<3.,max(maes)
    minimum_psnr=min(10*math.log10(255**2/max(v,1e-15)) for v in mses)
    assert minimum_psnr>30.,minimum_psnr
    assert len({s['decoded_rgb_sha256'] for s in scene_checks})==len(scene_checks)
    info['frame_count']=count
    return info,{'file':spec['stem']+'.mp4','decoded_all_frames':True,
                 'decoded_frames':count,'decode_errors':[],
                 'comparison':'Each decoded frame compared to the original GIF frame at the same timestamp; original675rows retained, no crop/scale.',
                 'maximum_frame_mean_absolute_rgb_error':max(maes),
                 'mean_frame_mean_absolute_rgb_error':float(np.mean(maes)),
                 'minimum_frame_psnr_db':minimum_psnr,
                 'scene_checks':scene_checks},thumbnails


def contact_sheet(items):
    thumb_w,thumb_h=600,338
    sheet=Image.new('RGB',(1200,math.ceil(len(items)/2)*(thumb_h+40)),'#091624')
    draw=ImageDraw.Draw(sheet)
    font_path=Path('C:/Windows/Fonts/segoeui.ttf')
    font=ImageFont.truetype(str(font_path),17) if font_path.exists() else ImageFont.load_default()
    for i,(label,image) in enumerate(items):
        x=(i%2)*thumb_w;y=(i//2)*(thumb_h+40)
        sheet.paste(image.resize((thumb_w,thumb_h),Image.Resampling.LANCZOS),(x,y))
        draw.text((x+15,y+thumb_h+8),label,font=font,fill='#f6f3eb')
    path=HERE/'video-validation/scenes-contact-sheet.png';sheet.save(path)
    return str(path.relative_to(HERE)).replace('\\','/')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ffmpeg',help='Optional path to an FFmpeg executable with libx264')
    parser.add_argument('--overwrite',action='store_true',help='Replace the generated MP4 files')
    parser.add_argument('--verify-only',action='store_true',help='Decode and verify existing videos without encoding')
    args=parser.parse_args();ffmpeg=ffmpeg_path(args.ffmpeg)
    version=subprocess.run([ffmpeg,'-version'],capture_output=True,text=True,check=True).stdout.splitlines()[0]
    manifest={'schema_version':1,'format':'MP4/H.264','encoder_version':version,
              'content_note':'Explanatory scientific diagrams, not laboratory footage. Original GIF content and12second timeline preserved.',
              'padding':'One background row added at bottom:1200x675source becomes1200x676. No cropping or scaling.',
              'encoding':'H.264 Constrained Baseline level3.1, yuv420p, CRF16,20fps, no audio, faststart moov before mdat.',
              'videos':[]}
    validation={'schema_version':1,'videos':[],'all_checks_passed':False}
    scenes=[]
    for spec in SPECS:
        source_path=HERE/(spec['stem']+'.gif');target=HERE/(spec['stem']+'.mp4')
        source=source_info(source_path)
        if source['duration_seconds']!=12.:raise ValueError('Original animation duration changed')
        if args.verify_only:
            staged=target
        else:
            if target.exists() and not args.overwrite:raise FileExistsError(f'{target.name} exists; use --overwrite or --verify-only')
            staged=HERE/(spec['stem']+'.pending.mp4')
            command=[ffmpeg,'-hide_banner','-loglevel','error','-nostdin','-y','-ignore_loop','1',
                     '-i',str(source_path),'-vf','pad=1200:676:0:0:color=0x091624,fps=20',
                     '-t','12','-an','-c:v','libx264','-preset','medium','-crf','16',
                     '-pix_fmt','yuv420p','-profile:v','baseline','-level','3.1','-tag:v','avc1',
                     '-movflags','+faststart','-fps_mode','cfr','-video_track_timescale','20000',
                     '-threads','2',str(staged)]
            subprocess.run(command,check=True,capture_output=True)
        info,checks,images=validate(ffmpeg,staged,source_path,spec,source)
        if not args.verify_only:staged.replace(target)
        assert sha256(source_path)==source['sha256'],'Original GIF changed during conversion'
        manifest['videos'].append({'file':target.name,'source_gif':source_path.name,
                                   'sha256':sha256(target),'source_sha256':source['sha256'],
                                   'bytes':target.stat().st_size,'source_info':source,**info})
        validation['videos'].append(checks);scenes.extend(images)
        print(target.name+': all240frames decoded,12seconds,1200x676,H.264/yuv420p,faststart',flush=True)
    validation['scene_contact_sheet']=contact_sheet(scenes)
    validation['all_checks_passed']=True
    manifest['converter_sha256']=sha256(Path(__file__))
    (HERE/'video_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
    (HERE/'video_validation.json').write_text(json.dumps(validation,indent=2)+'\n',encoding='utf8')
    print('Saved video_manifest.json and video_validation.json',flush=True)


if __name__=='__main__':main()
