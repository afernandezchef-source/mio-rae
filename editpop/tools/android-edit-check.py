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
PROJECT = WORK + '/PruebaUI'
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


def main():
    assert shell('getprop','ro.kernel.qemu') == '1', 'This script is for test emulators, not physical phones'
    run('adb', 'root')
    run('adb', 'wait-for-device')
    assert shell('id').startswith('uid=0'), 'Rooted test emulator required; never modifies a real phone'
    shell('am', 'force-stop', PKG)
    config = ROOT + '/app.concat.editor'
    shell('mkdir', '-p', config, WORK, ROOT + '/checks')
    prefs = {'locale':'es', 'accent':'coral', 'server':{'enabled':True,'listen':'127.0.0.1:7420','token':TEST_TOKEN}}
    run('adb', 'shell', f'cat > {shlex.quote(config+"/settings.json")}', data=json.dumps(prefs).encode())
    fixture = OUT / 'ClipTest.mp4'
    run('ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i', 'testsrc2=s=320x180:r=30:d=4', '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=48000:duration=4', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-shortest', str(fixture))
    run('adb', 'push', str(fixture), FIXTURE)
    # Root-written files must belong to the application before it writes recents/settings.
    uid = shell('stat', '-c', '%u', ROOT)
    shell('chown', '-R', f'{uid}:{uid}', config, ROOT + '/checks')
    shell('restorecon', '-RF', config, ROOT + '/checks')
    restart()
    run('adb', 'forward', 'tcp:7420', 'tcp:7420')
    rpc = Rpc()
    scenario = os.environ.get('EDITPOP_TEST_SCENARIO','full')
    assert scenario in ('full','ui-export'), scenario
    width,height = 1920,1080
    rpc.call('project.create', location=WORK, name='PruebaUI', video={'width':width,'height':height,'rateNum':30,'rateDen':1})
    imported = rpc.call('media.import', path=PROJECT, file=FIXTURE)
    project = imported['project']
    timeline = project['timelines'][0]
    rpc.call('edit.apply', path=PROJECT, command={'op':'addClip','mediaId':project['media'][0]['id'],'trackId':timeline['tracks'][0]['id'],'start':0,'ripple':False})
    rpc.call('project.save', path=PROJECT)
    rpc.call('project.close', path=PROJECT, save=True)
    rpc.close()
    restart()
    click_label('Prueba', '01-home')
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
    shot('FAIL')
    raise
finally:
    (OUT/'actions.json').write_text(json.dumps(LOG,indent=2))
    # Capture stalled native threads before the runner shuts down the emulator.
    pid = shell('pidof', PKG).split()
    if pid:
        for label, command in [('threads', ['adb','shell','ps','-T','-p',pid[0]]), ('native-stack', ['adb','shell','debuggerd','-b',pid[0]]), ('export-files', ['adb','shell','ls','-laR',PROJECT])]:
            try:
                result = sp.run(command, stdout=sp.PIPE, stderr=sp.STDOUT, timeout=25)
                (OUT/(label+'.txt')).write_bytes(result.stdout)
            except sp.TimeoutExpired as error:
                (OUT/(label+'.txt')).write_bytes(error.stdout or b'timeout')
    (OUT/'logcat.txt').write_bytes(run('adb','logcat','-d','-v','threadtime',check=False))
    run('adb','forward','--remove','tcp:7420',check=False)
