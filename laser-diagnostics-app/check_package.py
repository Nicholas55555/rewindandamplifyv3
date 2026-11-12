"""Verify the offline package and its source-evidence integrity."""
from pathlib import Path
from html.parser import HTMLParser
import hashlib
import json
import re

HERE=Path(__file__).resolve().parent
class CheckHTML(HTMLParser):
    def __init__(self):super().__init__();self.ids=[];self.urls=[];self.videos=[];self.current_video=None
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'id' in a:self.ids.append(a['id'])
        for key in ['src','href','poster']:
            if key in a:self.urls.append(a[key])
        if tag=='video':
            self.current_video={'attributes':a,'sources':[]};self.videos.append(self.current_video)
        if tag=='source' and self.current_video is not None:self.current_video['sources'].append(a)
    def handle_endtag(self,tag):
        if tag=='video':self.current_video=None

def boxes(data,start=0,end=None):
    """Parse bounded ISO-BMFF boxes rather than trusting a filename extension."""
    end=len(data) if end is None else end
    pos=start
    while pos<end:
        assert pos+8<=end, 'Truncated MP4 box header'
        size=int.from_bytes(data[pos:pos+4],'big');kind=data[pos+4:pos+8];header=8
        if size==1:
            assert pos+16<=end, 'Truncated large MP4 box'
            size=int.from_bytes(data[pos+8:pos+16],'big');header=16
        elif size==0:size=end-pos
        assert size>=header and pos+size<=end, 'Invalid MP4 box extent'
        yield {'kind':kind,'start':pos,'payload':pos+header,'end':pos+size}
        pos+=size

def child(data,parent,kind):
    matches=[b for b in boxes(data,parent['payload'],parent['end']) if b['kind']==kind]
    assert len(matches)==1, f'Expected exactly one MP4 {kind!r} box'
    return matches[0]

def verify_mp4(path,entry):
    data=path.read_bytes();top=list(boxes(data));types=[b['kind'] for b in top]
    assert types[0]==b'ftyp' and b'moov' in types and b'mdat' in types, 'Not a complete MP4'
    assert types.index(b'moov')<types.index(b'mdat'), 'MP4 is not configured for fast start'
    ftyp=top[0];brands=data[ftyp['payload']:ftyp['end']]
    assert any(brand in brands for brand in [b'isom',b'iso2',b'mp41',b'mp42',b'avc1']), 'Unsupported container brand'
    moov=next(b for b in top if b['kind']==b'moov');mvhd=child(data,moov,b'mvhd');p=mvhd['payload']
    version=data[p]
    assert version in [0,1], 'Unsupported movie header version'
    offset=12 if version==0 else 20
    scale=int.from_bytes(data[p+offset:p+offset+4],'big')
    duration=int.from_bytes(data[p+offset+4:p+offset+8+(4 if version else 0)],'big')
    assert scale>0 and abs(duration/scale-float(entry['duration_seconds']))<.01
    assert abs(duration/scale-12.)<.01, 'Unexpected video duration'
    tracks=[b for b in boxes(data,moov['payload'],moov['end']) if b['kind']==b'trak']
    assert len(tracks)==1, 'Expected one silent video track'
    mdia=child(data,tracks[0],b'mdia');hdlr=child(data,mdia,b'hdlr')
    assert data[hdlr['payload']+8:hdlr['payload']+12]==b'vide'
    stbl=child(data,child(data,mdia,b'minf'),b'stbl');stsd=child(data,stbl,b'stsd')
    sample_entries=list(boxes(data,stsd['payload']+8,stsd['end']))
    assert len(sample_entries)==1 and sample_entries[0]['kind']==b'avc1', 'Video is not AVC/H.264'
    avc=sample_entries[0];q=avc['payload']
    width=int.from_bytes(data[q+24:q+26],'big');height=int.from_bytes(data[q+26:q+28],'big')
    assert (width,height)==(1200,676)==(entry['width'],entry['height'])
    configs=[b for b in boxes(data,q+78,avc['end']) if b['kind']==b'avcC']
    assert len(configs)==1 and data[configs[0]['payload']]==1, 'Missing AVC decoder configuration'
    stsz=child(data,stbl,b'stsz');frame_count=int.from_bytes(data[stsz['payload']+8:stsz['payload']+12],'big')
    assert frame_count==entry['frame_count']==240
    assert abs(frame_count/(duration/scale)-float(entry['frame_rate']))<.01
    assert entry['codec']=='h264' and entry['pixel_format']=='yuv420p' and entry['faststart'] and not entry['audio']
    assert hashlib.sha256(data).hexdigest()==entry['sha256'], 'Video differs from conversion manifest'
    return {'file':path.name,'codec_sample_entry':'avc1','dimensions':[width,height],
            'duration_seconds':duration/scale,'frames':frame_count,'faststart':True}

def main():
    p=CheckHTML();p.feed((HERE/'index.html').read_text(encoding='utf8'))
    assert len(p.ids)==len(set(p.ids)), 'Duplicate HTML ids'
    for url in p.urls:
        assert not url.startswith(('http:','https:','//')), 'Page unexpectedly depends on network'
        if url=='#':continue
        if url.startswith('#'):assert url[1:] in p.ids,url
        else:assert (HERE/url.split('#')[0].split('?')[0]).is_file(),url
    for script in ['app.js','research.js','quantum-dots.js','joint-hom.js','hardware.js']:
        js=(HERE/script).read_text(encoding='utf8')
        for element in re.findall(r"\$\('([^']+)'\)",js):assert element in p.ids,(script,element)
        assert 'fetch(' not in js and 'XMLHttpRequest' not in js
    manifest=json.loads((HERE/'evidence/manifest.json').read_text())
    for rel,expected in manifest['files'].items():assert hashlib.sha256((HERE/rel).read_bytes()).hexdigest()==expected,rel
    assert all('research_'+key+'.json' in (HERE/'research-data.js').read_text(encoding='utf8') for key in ['frequency','drive','prior','phase','spatial','inference_ignored','inference_aware','dot','hom_reference','hom_analysis','joint_hom','dot_design','dot_design_validation','hardware'])
    hardware=json.loads((HERE/'evidence/research_hardware.json').read_text())
    assert hardware['status']=='complete' and hardware['jobs']==len(hardware['runs'])
    for rel,expected in hardware['input_sha256'].items():
        local=HERE/'evidence/hardware'/Path(rel).relative_to('hardware_campaign')
        assert hashlib.sha256(local.read_bytes()).hexdigest()==expected,rel
    for name in ['main/independent_review.json','exploratory_design/validation_run/independent_review.json','exploratory_design/hardware_bundle/independent_review.json']:
        assert json.loads((HERE/'evidence/joint-hom'/name).read_text())['all_checks_passed']
    reference=json.loads((HERE/'evidence/research_hom_reference.json').read_text())
    assert reference['all_checks_passed'] and len(reference['files'])==6
    assert reference['license']['id']=='CC-BY-4.0' and not reference['compatibility']['team_data']
    for entry in reference['files']:
        assert hashlib.sha256((HERE/'evidence/hom'/entry['path']).read_bytes()).hexdigest()==entry['sha256']
    dot=json.loads((HERE/'evidence/research_dot.json').read_text())
    assert dot['provenance']['all_quadrature_checks_passed']
    analysis=json.loads((HERE/'evidence/research_hom_analysis.json').read_text())
    assert analysis['reference_manifest_sha256']==hashlib.sha256((HERE/'evidence/research_hom_reference.json').read_bytes()).hexdigest()
    for entry in reference['files']:assert analysis['raw_sha256'][entry['path']]==entry['sha256']
    independent=json.loads((HERE/'evidence/hom_analysis_independent_primary.json').read_text())
    assert independent['results_sha256']==hashlib.sha256((HERE/'evidence/research_hom_analysis.json').read_bytes()).hexdigest()
    assert independent['all_primary_areas_centers_and_point_estimates_match']
    analysis_validation=json.loads((HERE/'evidence/hom_analysis_validation.json').read_text())
    assert analysis_validation['status']=='passed' and analysis_validation['unit_tests']['count']==14
    assert analysis_validation['artifact_sha256']['results.json']==independent['results_sha256']
    for name in ['HOM_ANALYSIS.md','HOM_ANALYSIS_PROTOCOL.md']:assert (HERE/'evidence'/name).is_file()
    drive=json.loads((HERE/'evidence/research_drive.json').read_text())
    prior=json.loads((HERE/'evidence/research_prior.json').read_text())
    assert len(drive['cases'])==13 and prior['main_results_sha256']==hashlib.sha256((HERE/'evidence/research_drive.json').read_bytes()).hexdigest()
    for name in ['drive_independent_review.json','prior_independent_review.json']:
        assert json.loads((HERE/'evidence'/name).read_text())['all_checks_passed']
    assert len(p.videos)==2, 'Expected two visible MP4 players'
    for player in p.videos:
        attrs=player['attributes']
        assert 'controls' in attrs and 'playsinline' in attrs and attrs.get('preload')=='metadata'
        assert 'autoplay' not in attrs and attrs.get('poster','').endswith('.png')
        assert len(player['sources'])==1 and player['sources'][0].get('type')=='video/mp4'
        assert player['sources'][0]['src'].endswith('.mp4')
    assert not any(url.endswith('.gif') for url in p.urls), 'A GIF is still offered as an app fallback'
    videos=json.loads((HERE/'assets/video_manifest.json').read_text())
    assert len(videos['videos'])==2
    checked=[verify_mp4(HERE/'assets'/Path(v['file']).name,v) for v in videos['videos']]
    print(json.dumps({'html_ids':len(p.ids),'local_links_checked':len(p.urls),'evidence_hashes':len(manifest['files']),
                      'network_runtime_dependencies':0,'videos':checked,'status':'passed'},indent=2))

if __name__=='__main__':main()
