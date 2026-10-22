#!/usr/bin/env python3
"""Real Android taps plus saved-document assertions. Synthetic media only.

Requires adb root (test emulator), ffmpeg, tesseract spa, Pillow. Uses Concat's
existing loopback API ONLY to seed a fresh project, never to perform the edits
under test. No test hooks or automation settings are added to a delivered APK.
"""
import csv
import io
import copy
import json
import os
import re
import shlex
import socket
import subprocess as sp
import sys
import time
from pathlib import Path
from PIL import Image, ImageOps

PKG = 'cl.kokumix.editpop.concatcandidate'
TEST_TOKEN = 'editpop-ci-only-loopback-token-0123456789abcdef'
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else 'android-edit-check')
OUT.mkdir(parents=True, exist_ok=True)
ROOT = f'/data/user/0/{PKG}/files'
WORK = f'/sdcard/Android/data/{PKG}/files/checks'
SCENARIO = os.environ.get('EDITPOP_TEST_SCENARIO', 'full')
PROJECT_NAME = {'scene-cuts':'EscenasUI','audio-cleanup':'AudioUI','stabilization':'CamaraUI'}.get(SCENARIO,'PruebaUI')
PROJECT = WORK + '/' + PROJECT_NAME
FIXTURE = ROOT + '/checks/ClipTest.mp4'
LOG = []


def run(*args, data=None, check=True):
    return sp.run(args, input=data, stdout=sp.PIPE, stderr=sp.PIPE, check=check, timeout=90).stdout


def shell(*args):
    return run('adb', 'shell', *args).decode().strip()


def shot(name):
    p = OUT / (name + '.png')
    p.write_bytes(run('adb', 'exec-out', 'screencap', '-p'))
    return p


def words(name, region=None, contrast=False):
    p = shot(name)
    offset = 0
    if region is not None:
        original = Image.open(p)
        offset = int(original.height * region[0])
        cropped = original.crop((0, offset, original.width, int(original.height * region[1])))
        if contrast == 'white':
            cropped = ImageOps.grayscale(cropped).point(lambda v: 0 if v > 185 else 255)
        elif contrast == 'gray':
            cropped = ImageOps.autocontrast(ImageOps.invert(ImageOps.grayscale(cropped)))
        p = OUT / (name + '-ocr.png')
        cropped.save(p)
    txt = run('tesseract', str(p), 'stdout', '-l', 'spa+eng', '--psm', '11', 'tsv').decode()
    (OUT / (name + '.tsv')).write_text(txt)
    rows = [row for row in csv.DictReader(io.StringIO(txt), delimiter='\t') if row['text'].strip()]
    for row in rows:
        row['top'] = str(int(row['top']) + offset)
    return rows


def tap(x, y):
    shell('input', 'tap', str(round(x)), str(round(y)))
    time.sleep(1)


def find(pattern, name, min_y=0, max_y=1):
    rows = words(name)
    w, h = Image.open(OUT / (name + '.png')).size
    found = [r for r in rows if min_y*h <= int(r['top']) <= max_y*h and re.search(pattern, r['text'], re.I)]
    for style in ['gray', 'white']:
        if found:
            break
        # OCR can skip a filmstrip caption or a gray search placeholder.
        # Keep the real screenshot coordinates; never substitute an edit.
        end = min(max_y, .70) if pattern == 'Buscar' else max_y
        rows = words(name+'-'+style, region=(min_y, end), contrast=style)
        found = [r for r in rows if re.search(pattern, r['text'], re.I)]
    if not found:
        raise AssertionError(f'{name}: label {pattern!r} absent; text={[r["text"] for r in rows]}')
    r = found[0]
    return int(r['left'])+int(r['width'])/2, int(r['top'])+int(r['height'])/2


def click_label(pattern, name, **kw):
    x, y = find(pattern, name, **kw)
    LOG.append({'tap': pattern, 'x': x, 'y': y})
    tap(x, y)
    return x, y


def toolbar(pattern, name):
    for i in range(6):
        try:
            click_label(pattern, f'{name}-{i}', min_y=.83)
            return
        except AssertionError:
            w, h = Image.open(OUT / f'{name}-{i}.png').size
            shell('input', 'swipe', str(int(w*.85)), str(int(h*.915)), str(int(w*.2)), str(int(h*.915)), '550')
            time.sleep(.6)
    raise AssertionError(f'toolbar label absent: {pattern}')


def document(name, predicate):
    until = time.monotonic() + 20
    last = None
    while time.monotonic() < until:
        raw = run('adb', 'exec-out', 'cat', PROJECT + '/concat.json')
        last = json.loads(raw)
        if predicate(last):
            (OUT / (name + '.json')).write_text(json.dumps(last, indent=2))
            return last
        time.sleep(.5)
    (OUT / (name + '-failed.json')).write_text(json.dumps(last, indent=2))
    raise AssertionError(f'{name}: saved project did not reach expected state')


class Rpc:
    def __init__(self):
        deadline = time.monotonic() + 30
        while True:
            try:
                self.s = socket.create_connection(('127.0.0.1', 7420), timeout=3)
                self.s.settimeout(60)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(.5)
        self.f = self.s.makefile('rwb')
        self.n = 0
        self.call('auth', token=TEST_TOKEN)

    def call(self, method, **params):
        self.n += 1
        call_deadline = time.monotonic() + 60
        with (OUT/'rpc-events.jsonl').open('a') as trail:
            trail.write(json.dumps({'phase':'request','id':self.n,'method':method})+'\n')
        self.f.write((json.dumps({'jsonrpc':'2.0', 'id':self.n, 'method':method, 'params':params})+'\n').encode())
        self.f.flush()
        while True:
            if time.monotonic() >= call_deadline:
                raise TimeoutError(f'API did not reply within 60s: {method}')
            line = self.f.readline()
            if not line:
                raise AssertionError('API connection closed')
            result = json.loads(line)
            with (OUT/'rpc-events.jsonl').open('a') as trail:
                trail.write(json.dumps({'phase':'received','id':result.get('id'),'method':result.get('method'),'error':result.get('error'),'params':result.get('params')})+'\n')
            if result.get('id') == self.n:
                assert 'error' not in result, result
                return result['result']

    def close(self):
        self.f.close()
        self.s.close()


def restart():
    shell('am', 'force-stop', PKG)
    activity = shell('cmd', 'package', 'resolve-activity', '--brief', '-c', 'android.intent.category.LAUNCHER', PKG).splitlines()[-1]
    shell('am', 'start', '-W', '-n', activity)
    time.sleep(4)



def ui_export_check():
    """Real Export buttons and MediaStore publication on a fresh emulator."""
    def export_tap(name, header):
        try:
            click_label('Exportar', name, **({'max_y':.2} if header else {'min_y':.65}))
            return
        except AssertionError:
            # Tesseract treats the rounded lime button as a graphic. Read
            # its interior alone, then tap the actual visible button.
            im = Image.open(OUT/(name+'.png')).convert('RGB')
            w,h = im.size
            left,top,right,bottom = (int(w*.65),int(h*.025),w,int(h*.09)) if header else (0,int(h*.8),w,int(h*.97))
            region = im.crop((left,top,right,bottom))
            mask = Image.new('L',region.size)
            mask.putdata([255 if r>150 and g>170 and b<150 else 0 for r,g,b in region.getdata()])
            box = mask.getbbox()
            assert box, f'{name}: no visible export button'
            x0,y0,x1,y1 = box; bw,bh=x1-x0,y1-y0
            word = region.crop((x0+int(bw*.28),y0+int(bh*.18),x1-int(bw*.06),y1-int(bh*.18))).convert('L').point(lambda v:255 if v>100 else 0)
            target = OUT/(name+'-button.png');word.resize((word.width*3,word.height*3)).save(target)
            label = run('tesseract',str(target),'stdout','-l','spa+eng','--psm','7').decode()
            assert re.search('Exportar',label,re.I), f'{name}: {label!r}'
            LOG.append({'tap':'Exportar from visible button OCR','x':left+(x0+x1)/2,'y':top+(y0+y1)/2})
            tap(left+(x0+x1)/2,top+(y0+y1)/2)
    export_tap('ui-export-open', True)
    time.sleep(2)
    export_tap('ui-export-start', False)
    until = time.monotonic()+180
    row = None
    while time.monotonic()<until:
        listing = shell('content','query','--uri','content://media/external/video/media',
                        '--projection','_id:_display_name:relative_path:is_pending:_data:_size')
        (OUT/'ui-export-mediastore.txt').write_text(listing)
        rows = [line for line in listing.splitlines() if 'Movies/EditPop/' in line and 'is_pending=0' in line]
        if rows:
            row = rows[-1]
            break
        time.sleep(2)
    assert row, 'Export button did not publish a completed video to Movies/EditPop within180s'
    match = re.search(r'_data=(.*?)(?:, |$)', row)
    assert match and match[1].startswith('/storage/emulated/0/Movies/EditPop/'), row
    exported = OUT/'ui-gallery-result.mp4'
    run('adb','pull',match[1],str(exported))
    probe = json.loads(run('ffprobe','-v','error','-show_streams','-show_format','-of','json',str(exported)))
    (OUT/'ui-export-probe.json').write_text(json.dumps(probe,indent=2))
    video = next(stream for stream in probe['streams'] if stream['codec_type']=='video')
    assert (video['width'],video['height'])==(1920,1080),probe
    assert all(video.get(k)=='bt709' for k in ('color_space','color_transfer','color_primaries')),video
    assert video.get('color_range')=='tv',video
    assert abs(float(probe['format']['duration'])-4)<.1,probe
    assert any(stream['codec_type']=='audio' for stream in probe['streams']),probe
    run('ffmpeg','-xerror','-v','error','-i',str(exported),'-f','null','-')
    shot('ui-export-published')
    (OUT/'PASS-ui-export.json').write_text(json.dumps({'result':'PASS','scope':'Real UI Export buttons, H264/AAC1080p and completed MediaStore publication; synthetic project; no Samsung test','actions':LOG},indent=2))


def transport_tap(label):
    """Tap the real transport control; no editor API or keyboard substitution."""
    import xml.etree.ElementTree as ET
    nodes = []
    try:
        shell('uiautomator', 'dump', '/sdcard/editpop-window.xml')
        raw = run('adb', 'exec-out', 'cat', '/sdcard/editpop-window.xml')
        (OUT/(label+'-accessibility.xml')).write_bytes(raw)
        nodes = list(ET.fromstring(raw).iter('node'))
    except (sp.SubprocessError, ET.ParseError):
        pass
    for node in nodes:
        if label.lower() in (node.get('content-desc','').lower(), node.get('text','').lower()):
            bounds = [int(v) for v in re.findall(r'\d+',node.get('bounds',''))]
            if len(bounds)==4 and bounds[2]>bounds[0] and bounds[3]>bounds[1]:
                LOG.append({'accessible tap':label,'bounds':bounds})
                tap((bounds[0]+bounds[2])/2,(bounds[1]+bounds[3])/2)
                return
    # Slint's NativeActivity may expose no virtual accessibility nodes. On this
    # fixed API30/Pixel6 profile, locate the actual enabled white transport icon.
    # The saved document assertion afterwards must prove the button took effect.
    assert label in ('Deshacer','Rehacer')
    im = Image.open(shot(label+'-transport')).convert('RGB')
    w,h = im.size
    left,right = (.83,.89) if label=='Deshacer' else (.92,.97)
    x0,y0,x1,y1 = int(w*left),int(h*.53),int(w*right),int(h*.59)
    region = im.crop((x0,y0,x1,y1))
    mask = Image.new('L',region.size)
    mask.putdata([255 if min(r,g,b)>170 else 0 for r,g,b in region.getdata()])
    box = mask.getbbox()
    assert box and sum(v>0 for v in mask.getdata())>25, f'No enabled visible {label} icon'
    a,b,c,d=box
    LOG.append({'tap':label,'method':'visible enabled transport icon on fixed emulator','bounds':[x0+a,y0+b,x0+c,y0+d]})
    tap(x0+(a+c)/2,y0+(b+d)/2)


def scene_cuts_check():
    before = document('scene-before', lambda d:len(d.get('clips',[]))==1)
    toolbar('Sugerir', 'scene-open')
    deadline = time.monotonic()+90
    while True:
        rows = words('scene-review',region=(.4,.96),contrast='gray')
        if any(re.search('marcados',r['text'],re.I) for r in rows) and any('00:02' in r['text'] for r in rows):
            break
        assert time.monotonic()<deadline, 'No scene proposal at2s'
        time.sleep(1)
    assert document('scene-unmodified',lambda d:len(d.get('clips',[]))==1)==before
    click_label('Descartar','scene-discard',min_y=.4)
    assert document('scene-discarded',lambda d:len(d.get('clips',[]))==1)==before
    toolbar('Sugerir', 'scene-open-again')
    deadline = time.monotonic()+90
    while True:
        try:
            click_label('00:02', 'scene-select-proposal',min_y=.4)
            break
        except AssertionError:
            assert time.monotonic()<deadline
            time.sleep(1)
    rows = words('scene-preview-button',region=(.4,.96),contrast='gray')
    matches = [r for r in rows if re.fullmatch('Ver',r['text'],re.I)]
    assert matches, 'No preview button'
    # The instructions also say Ver: choose the button at the right of the row.
    button = max(matches,key=lambda r:int(r['left']))
    LOG.append({'tap':'Ver button on proposal row'})
    tap(int(button['left'])+int(button['width'])/2,int(button['top'])+int(button['height'])/2)
    deadline = time.monotonic()+20
    while True:
        picture = Image.open(shot('scene-preview-visible')).convert('RGB')
        red,green,blue = picture.getpixel((picture.width//2,int(picture.height*.22)))
        if blue>red+80 and blue>green+80:
            break
        assert time.monotonic()<deadline, ('Preview did not reach blue scene',red,green,blue)
        time.sleep(1)
    try:
        click_label('Aplicar','scene-apply',min_y=.4)
    except AssertionError:
        # As with Export, PSM11 can skip text on the accent-filled button.
        # Find its full-width colored rectangle, then verify its own label.
        im=Image.open(OUT/'scene-apply.png').convert('RGB')
        w,h=im.size
        rows=[]
        for y in range(int(h*.4),int(h*.95)):
            count=sum(r>150 and g>170 and b<150 for r,g,b in
                      im.crop((0,y,w,y+1)).getdata())
            if count>w*.7:
                rows.append(y)
        assert rows, 'No full-width enabled Apply button'
        top,bottom=min(rows),max(rows)
        button=im.crop((int(w*.2),top+int((bottom-top)*.15),int(w*.94),bottom-int((bottom-top)*.15)))
        p=OUT/'scene-apply-button.png'
        button.convert('L').point(lambda v:255 if v>100 else 0).save(p)
        text=run('tesseract',str(p),'stdout','-l','spa+eng','--psm','7').decode()
        assert re.search('Aplicar',text,re.I), text
        LOG.append({'tap':'Aplicar cortes marcados','method':'visible full-width button OCR','y':(top+bottom)/2})
        tap(w/2,(top+bottom)/2)
    edited = document('scene-applied',lambda d:len(d.get('clips',[]))==2)
    clips = sorted(edited['clips'],key=lambda c:c['start'])
    assert abs(clips[1]['start']-2)<1/30+.001, clips
    assert abs(sum(c['duration'] for c in clips)-4)<.001
    transport_tap('Deshacer')
    assert document('scene-undone',lambda d:len(d.get('clips',[]))==1)==before
    transport_tap('Rehacer')
    assert document('scene-redone',lambda d:len(d.get('clips',[]))==2)==edited
    restart()
    click_label('Escenas','scene-reopen')
    time.sleep(3)
    assert document('scene-reopened',lambda d:len(d.get('clips',[]))==2)==edited
    # Remove the prior full-regression export so publication must be new.
    shell('content','delete','--uri','content://media/external/video/media')
    ui_export_check()
    # Check the actual encoded image and sound, not only container metadata.
    import array
    import math
    measurements = {}
    for second, channel in [(1,0),(3,2)]:
        rgb = run('ffmpeg','-v','error','-ss',str(second),'-i',str(OUT/'ui-gallery-result.mp4'),
                  '-vf','crop=2:2:(iw-2)/2:(ih-2)/2,scale=1:1','-frames:v','1','-pix_fmt','rgb24','-f','rawvideo','-')
        assert len(rgb)==3, rgb
        assert rgb[channel]>150 and rgb[channel]-rgb[2-channel]>100, list(rgb)
        pcm = array.array('f')
        pcm.frombytes(run('ffmpeg','-v','error','-ss',str(second),'-i',str(OUT/'ui-gallery-result.mp4'),
                          '-t','0.25','-ac','1','-ar','48000','-f','f32le','-'))
        assert len(pcm)>1000
        rms = math.sqrt(sum(v*v for v in pcm)/len(pcm))
        real = sum(v*math.cos(2*math.pi*440*i/48000) for i,v in enumerate(pcm))
        imag = sum(v*math.sin(2*math.pi*440*i/48000) for i,v in enumerate(pcm))
        tone = 2*math.hypot(real,imag)/len(pcm)
        assert rms>.02 and tone>.05, (rms,tone)
        measurements[str(second)]={'center_rgb':list(rgb),'audio_rms':rms,'tone_440Hz_amplitude':tone}
    (OUT/'scene-export-measurements.json').write_text(json.dumps(measurements,indent=2))
    (OUT/'PASS-scene-cuts.json').write_text(json.dumps({'result':'PASS','scope':'Actual Android UI: local scene detection, discard, select, preview, apply, atomic undo/redo, save/reopen,1080p export; synthetic red/blue with flash; no physical Samsung test','actions':LOG},indent=2))


def export_control_document(edited,field,name):
    """Counterfactual export, same model/codec with only the target property off."""
    im=Image.open(shot('audio-export-done'));w,h=im.size
    tap(w*.93,h*.055)
    tap(w*.055,h*.055)
    rpc=Rpc()
    control=copy.deepcopy(edited)
    control['name']=name
    for entries in [control['clips'],control['timelines'][0]['clips']]:
        for clip in entries:
            if field=='filters': clip[field]=[]
            else: clip.pop(field,None)
    path=WORK+'/'+name
    rpc.call('project.create',location=WORK,name=name,video=edited['video'])
    rpc.call('project.close',path=path,save=True)
    run('adb','shell','cat > '+shlex.quote(path+'/concat.json'),data=json.dumps(control).encode())
    rpc.call('project.open',path=path)
    job=rpc.call('export.run',path=path,output=path+'/control.mp4',width=1920,height=1080,preset='ultrafast')['job']
    deadline=time.monotonic()+300
    while time.monotonic()<deadline:
        state=rpc.call('export.status',job=job)
        if state['state']!='running':
            assert state['state']=='done',state
            break
        time.sleep(2)
    else: raise AssertionError('Control export timed out')
    rpc.call('project.close',path=path,save=False);rpc.close()
    run('adb','pull',path+'/control.mp4',str(OUT/(name+'.mp4')))
    return OUT/(name+'.mp4')


def audio_cleanup_check():
    """Real noise switch, persistence, gallery export and matched codec control."""
    import array
    import math
    before=document('audio-before',lambda d:len(d.get('clips',[]))==1)
    toolbar('^Audio$', 'audio-open')
    for attempt in range(8):
        try:
            _,y=find('Reducir','audio-noise-row-'+str(attempt),min_y=.45,max_y=.90)
            im=Image.open(OUT/('audio-noise-row-'+str(attempt)+'.png'))
            tap(im.width*.92,y)  # actual switch at the right of this label
            break
        except AssertionError:
            im=Image.open(shot('audio-scroll-'+str(attempt)))
            shell('input','swipe',str(int(im.width*.65)),str(int(im.height*.85)),
                  str(int(im.width*.65)),str(int(im.height*.55)),'550')
            time.sleep(1)
    else:
        raise AssertionError('Reduce noise control not reachable')
    edited=document('audio-filter-enabled',lambda d:any(
        any(f['id']=='concat.denoise' and f.get('enabled',True) for f in c.get('filters',[]))
        for c in d.get('clips',[])))
    filters=edited['clips'][0]['filters']
    assert len(filters)==1 and abs(edited['clips'][0]['volume']-1)<1e-9
    im=Image.open(shot('audio-noise-enabled'))
    tap(im.width*.5,im.height*.2)  # dismiss sheet
    restart()
    click_label('^Audio','audio-reopen')
    time.sleep(3)
    assert document('audio-reopened',lambda d:bool(d['clips'][0].get('filters')))==edited
    ui_export_check()
    shutil=__import__('shutil')
    shutil.copy2(OUT/'ui-gallery-result.mp4',OUT/'audio-filtered.mp4')
    control_file=export_control_document(edited,'filters','AudioControl')
    def measure(file,at):
        pcm=array.array('f')
        pcm.frombytes(run('ffmpeg','-v','error','-ss',str(at),'-i',str(file),
                          '-t','1','-ac','1','-ar','48000','-f','f32le','-'))
        assert len(pcm)>=47000
        n=len(pcm);dc=sum(pcm)/n
        sine=[math.sin(2*math.pi*440*i/48000) for i in range(n)]
        cosine=[math.cos(2*math.pi*440*i/48000) for i in range(n)]
        a=2*sum((v-dc)*x for v,x in zip(pcm,sine))/n
        b=2*sum((v-dc)*x for v,x in zip(pcm,cosine))/n
        residual=math.sqrt(sum((v-dc-a*x-b*y)**2 for v,x,y in zip(pcm,sine,cosine))/n)
        return {'tone_amplitude':math.hypot(a,b),'residual_rms':residual,'peak':max(abs(v) for v in pcm)}
    measurements={}
    for at in [1,2.5]:
        control=measure(control_file,at)
        filtered=measure(OUT/'audio-filtered.mp4',at)
        reduction=20*math.log10(control['residual_rms']/filtered['residual_rms'])
        tone_change=20*math.log10(filtered['tone_amplitude']/control['tone_amplitude'])
        assert reduction>=6,(at,reduction,control,filtered)
        assert abs(tone_change)<1.5 and filtered['peak']<.98,(at,tone_change,filtered)
        measurements[str(at)]={'control':control,'filtered':filtered,'residual_reduction_db':reduction,'tone_change_db':tone_change}
    (OUT/'audio-cleanup-measurements.json').write_text(json.dumps(measurements,indent=2))
    (OUT/'PASS-audio-cleanup.json').write_text(json.dumps({'result':'PASS','scope':'Android30 actual Reduce noise switch, save/reopen, UI1080p export; matched Android export without filter; stationary synthetic noise and440Hz tone, not real voice or Samsung','measurements':measurements,'actions':LOG},indent=2))


def stabilization_check():
    """Actual stabilization switch; tracked motion, persistence and output jitter."""
    import math
    toolbar('^Editar$', 'stabilize-open')
    for attempt in range(12):
        try:
            _,y=find('Estabilizar','stabilize-row-'+str(attempt),min_y=.44,max_y=.90)
            im=Image.open(OUT/('stabilize-row-'+str(attempt)+'.png'))
            tap(im.width*.06,y)  # actual checkbox BEFORE the section title
            break
        except AssertionError:
            im=Image.open(shot('stabilize-scroll-'+str(attempt)))
            shell('input','swipe',str(int(im.width*.65)),str(int(im.height*.85)),
                  str(int(im.width*.65)),str(int(im.height*.55)),'550')
            time.sleep(1)
    else: raise AssertionError('Stabilize control not reachable')
    edited=document('stabilize-enabled',lambda d:bool(d['clips'][0].get('stabilize')))
    deadline=time.monotonic()+120
    measured=[]
    while time.monotonic()<deadline:
        paths=run('adb','shell','find',PROJECT+'/cache/stabilize','-name','motion',check=False).decode().splitlines()
        if paths and paths[0].startswith(PROJECT+'/'):
            text=run('adb','exec-out','cat',paths[0]).decode()
            (OUT/'stabilization-motion.txt').write_text(text)
            measured=[line.split() for line in text.splitlines() if line.startswith('f ')]
            coverage=[line.split() for line in text.splitlines() if line.startswith('covered ')]
            if len(measured)>=115 and any(float(line[2])>=4 for line in coverage): break
        time.sleep(1)
    else: raise AssertionError('Stabilization analysis did not finish')
    tracked=sum(line[2]=='t' for line in measured)
    assert tracked/len(measured)>.8,(tracked,len(measured))
    im=Image.open(shot('stabilize-measured'));tap(im.width*.5,im.height*.2)
    restart();click_label('Camara','stabilize-reopen');time.sleep(3)
    assert document('stabilize-reopened',lambda d:bool(d['clips'][0].get('stabilize')))==edited
    ui_export_check()
    filtered=OUT/'stabilized.mp4'
    __import__('shutil').copy2(OUT/'ui-gallery-result.mp4',filtered)
    control=export_control_document(edited,'stabilize','CameraControl')
    def marker_jitter(file):
        decoder=sp.Popen(['ffmpeg','-v','error','-i',str(file),'-an','-vf','scale=320:180',
                         '-pix_fmt','rgb24','-f','rawvideo','-'],stdout=sp.PIPE,stderr=sp.PIPE)
        positions=[];index=0
        while True:
            frame=decoder.stdout.read(320*180*3)
            if not frame: break
            assert len(frame)==320*180*3
            if 15<=index<105:
                xs=ys=count=0
                for pixel in range(0,len(frame),3):
                    r,g,b=frame[pixel:pixel+3]
                    if r>150 and g<90 and b<90:
                        at=pixel//3;xs+=at%320;ys+=at//320;count+=1
                assert count>40,(file.name,index,count)
                positions.append((xs/count,ys/count))
            index+=1
        error=decoder.stderr.read();assert decoder.wait()==0,error
        assert index==120 and len(positions)==90,(index,len(positions))
        mx=sum(x for x,y in positions)/len(positions);my=sum(y for x,y in positions)/len(positions)
        rms=math.sqrt(sum((x-mx)**2+(y-my)**2 for x,y in positions)/len(positions))
        return {'jitter_rms_at_320x180_px':rms,'positions':positions,'frames':index}
    original=marker_jitter(control);corrected=marker_jitter(filtered)
    assert original['jitter_rms_at_320x180_px']>3,original
    ratio=corrected['jitter_rms_at_320x180_px']/original['jitter_rms_at_320x180_px']
    assert ratio<.6,ratio
    result={'control':original,'stabilized':corrected,'residual_ratio':ratio,'tracked_frames':tracked,'measured_frames':len(measured)}
    (OUT/'stabilization-measurements.json').write_text(json.dumps(result,indent=2))
    (OUT/'PASS-stabilization.json').write_text(json.dumps({'result':'PASS','scope':'Android30 actual Stabilize switch, analysis cache, save/reopen and1080p UI export; camera jitter measured against matched uncorrected Android export; synthetic pure translation, not real footage or physical Samsung','measurements':result,'actions':LOG},indent=2))


def main():
    assert shell('getprop','ro.kernel.qemu') == '1', 'This script is for test emulators, not physical phones'
    # Restarting adbd can close its transport before the client gets an exit
    # status. Require a verified root shell after reconnecting, not root's exit.
    rooted = False
    for attempt in range(4):
        result = sp.run(['adb','root'],stdout=sp.PIPE,stderr=sp.STDOUT,timeout=30)
        with (OUT/'adb-root.log').open('ab') as trail:
            trail.write(result.stdout)
        run('adb', 'wait-for-device')
        time.sleep(1)
        try:
            if shell('id').startswith('uid=0'):
                rooted = True
                break
        except sp.SubprocessError:
            pass
        time.sleep(1)
    assert rooted, 'Rooted test emulator required; never modifies a real phone'
    shell('am', 'force-stop', PKG)
    config = ROOT + '/app.concat.editor'
    shell('mkdir', '-p', config, WORK, ROOT + '/checks')
    prefs = {'locale':'es', 'accent':'coral', 'server':{'enabled':True,'listen':'127.0.0.1:7420','token':TEST_TOKEN}}
    run('adb', 'shell', f'cat > {shlex.quote(config+"/settings.json")}', data=json.dumps(prefs).encode())
    fixture = OUT / 'ClipTest.mp4'
    source = 'color=red:s=180x320:r=30:d=4' if SCENARIO=='scene-cuts' else 'testsrc2=s=320x180:r=30:d=4'
    extra = ['-vf', "drawbox=c=blue:t=fill:enable='gte(t,2)',drawbox=c=white:t=fill:enable='between(t,0.5,0.55)'"] if SCENARIO=='scene-cuts' else []
    if SCENARIO=='stabilization':
        import random
        from PIL import ImageDraw
        rng=random.Random(42)
        texture=Image.new('RGB',(360,220));draw=ImageDraw.Draw(texture)
        for y in range(0,220,8):
            for x in range(0,360,8):
                gray=rng.randrange(30,220)
                draw.rectangle((x,y,x+7,y+7),fill=(gray,gray,gray))
        draw.rectangle((174,104,185,115),fill=(240,15,15))
        texture.save(OUT/'static-texture.png')
        run('ffmpeg','-y','-v','error','-loop','1','-framerate','30','-i',str(OUT/'static-texture.png'),
            '-f','lavfi','-i','sine=frequency=440:sample_rate=48000:duration=4',
            '-vf','crop=320:180:20+8*sin(2*PI*3*t):20+5*sin(2*PI*2*t)',
            '-t','4','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-shortest',str(fixture))
    elif SCENARIO=='audio-cleanup':
        run('ffmpeg','-y','-v','error','-f','lavfi','-i',source,
            '-f','lavfi','-i','aevalsrc=0.1*sin(2*PI*440*t):s=48000:d=4',
            '-f','lavfi','-i','anoisesrc=c=white:a=0.02:r=48000:d=4:s=123456',
            '-filter_complex','[1:a][2:a]amix=inputs=2:normalize=0[a]',
            '-map','0:v','-map','[a]','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-shortest',str(fixture))
    else:
        run('ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i', source, '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=48000:duration=4', *extra, '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-shortest', str(fixture))
    run('adb', 'push', str(fixture), FIXTURE)
    # Root-written files must belong to the application before it writes recents/settings.
    uid = shell('stat', '-c', '%u', ROOT)
    shell('chown', '-R', f'{uid}:{uid}', config, ROOT + '/checks')
    shell('restorecon', '-RF', config, ROOT + '/checks')
    restart()
    run('adb', 'forward', 'tcp:7420', 'tcp:7420')
    rpc = Rpc()
    scenario = os.environ.get('EDITPOP_TEST_SCENARIO','full')
    assert scenario in ('full','ui-export','scene-cuts','audio-cleanup','stabilization'), scenario
    width,height = 1920,1080
    rpc.call('project.create', location=WORK, name=PROJECT_NAME, video={'width':width,'height':height,'rateNum':30,'rateDen':1})
    imported = rpc.call('media.import', path=PROJECT, file=FIXTURE)
    project = imported['project']
    timeline = project['timelines'][0]
    rpc.call('edit.apply', path=PROJECT, command={'op':'addClip','mediaId':project['media'][0]['id'],'trackId':timeline['tracks'][0]['id'],'start':0,'ripple':False})
    rpc.call('project.save', path=PROJECT)
    rpc.call('project.close', path=PROJECT, save=True)
    rpc.close()
    restart()
    click_label({'scene-cuts':'Escenas','audio-cleanup':'^Audio','stabilization':'Camara'}.get(scenario,'Prueba'), '01-home')
    time.sleep(3)
    if scenario=='ui-export':
        ui_export_check()
        return
    # A real body tap places the playhead inside the clip. Its header is
    # found on screen, not by an internal callback or edit command.
    for attempt in range(4):
        try:
            click_label('ClipTest', f'02-editor-{attempt}', min_y=.55, max_y=.88)
            break
        except AssertionError:
            w, h = Image.open(OUT/f'02-editor-{attempt}.png').size
            shell('input', 'swipe', str(int(w*.3)), str(int(h*.81)), str(int(w*.3)), str(int(h*.64)), '500')
            time.sleep(1)
    else:
        raise AssertionError('Imported clip is not reachable on the timeline')
    if scenario=='scene-cuts':
        scene_cuts_check()
        return
    if scenario=='audio-cleanup':
        audio_cleanup_check()
        return
    if scenario=='stabilization':
        stabilization_check()
        return
    toolbar('Dividir', '03-split')
    d = document('04-split', lambda d: len(d.get('clips', [])) == 2)
    clips = sorted(d['clips'], key=lambda c:c['start'])
    assert 0 < clips[1]['start'] < 4
    assert abs(sum(c['duration'] for c in clips)-4) < .04
    right_id = clips[1]['id']
    toolbar('Efect', '05-effects')
    _, effect_search_y = click_label('Buscar', '06-effect-search', min_y=.4)
    shell('input', 'text', 'Pixelate')
    shell('input', 'keyevent', '4')
    time.sleep(1)
    # Search text itself is above the cards; choose the lower match.
    rows = words('07-effect-results', region=(.4, .95), contrast='gray')
    matches = [r for r in rows if re.search('pixel', r['text'], re.I) and int(r['top']) > effect_search_y + 50]
    assert matches, 'Search result card not rendered'
    r = max(matches, key=lambda r:int(r['top']))
    tap(int(r['left'])+int(r['width'])/2, int(r['top'])+int(r['height'])/2-30)
    d = document('08-effect', lambda d:any(c['id']==right_id and any(e['id']=='concat.pixelate' for e in c.get('videoEffects',[])) for c in d.get('clips',[])))
    shot('09-effect-applied')
    w, h = Image.open(OUT/'09-effect-applied.png').size
    tap(w*.5, h*.2)  # dismiss sheet
    toolbar('Trans', '10-transitions')
    try:
        _, transition_search_y = click_label('Buscar', '11-transition-search', min_y=.4)
    except AssertionError:
        # The gray placeholder can be dropped by OCR even in a crop. On
        # this fixed API30/Pixel6 profile, the search field is one header
        # below the recognized sheet title; touch that real field. The
        # following result and project assertions still require the UI edit.
        _, title_y = find('Transiciones', '11-transition-title', min_y=.4, max_y=.55)
        transition_search_y = title_y + w*.125
        LOG.append({'tap':'transition search below sheet title','x':w*.25,'y':transition_search_y})
        tap(w*.25, transition_search_y)
    shell('input','text','soft%scross-dissolve')
    shell('input','keyevent','4')
    time.sleep(1)
    rows = words('12-transition-results', region=(.4, .95), contrast='gray')
    matches = [r for r in rows if re.search('dissolve', r['text'], re.I) and int(r['top']) > transition_search_y + 50]
    assert matches, 'Transition result card not rendered'
    r = max(matches, key=lambda r:int(r['top']))
    tap(int(r['left'])+int(r['width'])/2, int(r['top'])+int(r['height'])/2-30)
    d = document('13-transition', lambda d:any(c['id']==right_id and (c.get('transitionIn') or {}).get('id')=='concat.dissolve' for c in d.get('clips',[])))
    assert d['clips'][0]['duration'] + d['clips'][1]['duration'] > 3.99
    tap(w*.5, h*.2)
    shot('14-finished-editor')
    restart()
    click_label('Prueba','15-reopen')
    time.sleep(3)
    shot('16-reopened-editor')
    reopened = document('17-reopened', lambda d:len(d.get('clips',[]))==2)
    assert reopened == d, 'Saved edits changed on reopening'
    # Save/close through the actual top-left button, then use the engine
    # API to render that exact UI-produced document, without further edits.
    tap(w*.055, h*.055)
    time.sleep(2)
    rpc = Rpc()
    rpc.call('project.open', path=PROJECT)
    result = rpc.call('export.run', path=PROJECT, output=PROJECT+'/ui-result.mp4', width=1920,height=1080, preset='ultrafast')
    (OUT/'18-export-started.json').write_text(json.dumps(result,indent=2))
    deadline = time.monotonic()+300
    while time.monotonic()<deadline:
        state = rpc.call('export.status', job=result['job'])
        (OUT/'19-export-status.json').write_text(json.dumps(state,indent=2))
        if state['state'] != 'running':
            assert state['state']=='done', state
            break
        time.sleep(2)
    else:
        raise AssertionError(f'Export did not complete within 300s: {state}')
    # Prove that the renderer actually uses these properties. Render a
    # control with only the effect removed, and one with only the transition
    # removed. The UI-produced document itself is never modified by these
    # controls, and both mirrors of a control's active timeline are changed.
    cut = clips[1]['start']
    effect_at = round(min(3.7, cut + .75)*30)/30
    transition_at = round((cut + .1)*30)/30
    for label, at in [('effect', effect_at), ('transition', transition_at)]:
        rpc.call('preview.frame', path=PROJECT, time=at,
                 output=PROJECT+'/'+label+'-actual.png', width=1920, height=1080)
        run('adb','pull',PROJECT+'/'+label+'-actual.png',str(OUT/(label+'-actual.png')))
        control = copy.deepcopy(d)
        control['name'] = 'Control-'+label
        for entries in [control['clips'], control['timelines'][0]['clips']]:
            for entry in entries:
                if entry['id'] == right_id:
                    if label == 'effect':
                        entry['videoEffects'] = []
                    else:
                        entry.pop('transitionIn', None)
        control_path = WORK+'/Control-'+label
        rpc.call('project.create', location=WORK, name='Control-'+label, video=d['video'])
        rpc.call('project.close', path=control_path, save=True)
        run('adb','shell','cat > '+shlex.quote(control_path+'/concat.json'),data=json.dumps(control).encode())
        rpc.call('project.open', path=control_path)
        rpc.call('preview.frame', path=control_path, time=at,
                 output=control_path+'/control.png', width=1920,height=1080)
        run('adb','pull',control_path+'/control.png',str(OUT/(label+'-control.png')))
        rpc.call('project.close', path=control_path, save=False)
    rpc.call('project.close', path=PROJECT, save=True)
    rpc.close()
    run('adb','pull',PROJECT+'/ui-result.mp4',str(OUT/'ui-result.mp4'))
    probe = json.loads(run('ffprobe','-v','error','-show_streams','-show_format','-of','json',str(OUT/'ui-result.mp4')))
    (OUT/'export-probe.json').write_text(json.dumps(probe,indent=2))
    video = next(s for s in probe['streams'] if s['codec_type']=='video')
    assert (video['width'],video['height'])==(1920,1080)
    assert all(video.get(k)=='bt709' for k in ('color_space','color_transfer','color_primaries')),video
    assert video.get('color_range')=='tv',video
    assert abs(float(probe['format']['duration'])-4)<.1
    assert any(s['codec_type']=='audio' for s in probe['streams'])
    run('ffmpeg','-xerror','-v','error','-i',str(OUT/'ui-result.mp4'),'-f','null','-')
    from PIL import ImageChops, ImageStat
    scores = {}
    for label, at in [('effect', effect_at), ('transition', transition_at)]:
        actual = Image.open(OUT/(label+'-actual.png')).convert('RGB')
        control = Image.open(OUT/(label+'-control.png')).convert('RGB')
        scores[label+'_difference_from_control'] = sum(ImageStat.Stat(ImageChops.difference(actual,control)).mean)/3
        assert scores[label+'_difference_from_control'] > .5, f'{label} not visible in rendered frame: {scores}'
        frame = OUT/(label+'-export.png')
        run('ffmpeg','-y','-v','error','-i',str(OUT/'ui-result.mp4'),'-ss',str(at),'-frames:v','1',str(frame))
        encoded = Image.open(frame).convert('RGB')
        scores[label+'_export_error'] = sum(ImageStat.Stat(ImageChops.difference(actual,encoded)).mean)/3
        assert scores[label+'_export_error'] < 4, f'Preview/export disagree: {scores}'
        scores[label+'_export_vs_control_error'] = sum(ImageStat.Stat(ImageChops.difference(control,encoded)).mean)/3
        assert scores[label+'_export_error'] < scores[label+'_export_vs_control_error'], f'Export closer to unedited control: {scores}'
    (OUT/'visual-verification.json').write_text(json.dumps(scores,indent=2))
    # Complete the same edited document through the user's Export buttons.
    restart()
    click_label('Prueba','ui-reopen-for-export')
    time.sleep(3)
    ui_export_check()
    (OUT/'PASS.json').write_text(json.dumps({'result':'PASS','scope':'real taps split, effect, transition; saved/reopened; same document exported via engine API and real UI at1080p, BT709, completed gallery publication; no Samsung test','actions':LOG},indent=2))


try:
    main()
except Exception:
    try:
        shot('FAIL')
    except sp.SubprocessError:
        pass
    raise
finally:
    (OUT/'actions.json').write_text(json.dumps(LOG,indent=2))
    # Capture stalled native threads before the runner shuts down the emulator.
    pid = run('adb','shell','pidof',PKG,check=False).decode().split()
    if pid:
        for label, command in [('threads', ['adb','shell','ps','-T','-p',pid[0]]), ('native-stack', ['adb','shell','debuggerd','-b',pid[0]]), ('export-files', ['adb','shell','ls','-laR',PROJECT])]:
            try:
                result = sp.run(command, stdout=sp.PIPE, stderr=sp.STDOUT, timeout=25)
                (OUT/(label+'.txt')).write_bytes(result.stdout)
            except sp.TimeoutExpired as error:
                (OUT/(label+'.txt')).write_bytes(error.stdout or b'timeout')
    (OUT/'logcat.txt').write_bytes(run('adb','logcat','-d','-v','threadtime',check=False))
    run('adb','forward','--remove','tcp:7420',check=False)
