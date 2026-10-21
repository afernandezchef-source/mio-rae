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
        self.f.write((json.dumps({'jsonrpc':'2.0', 'id':self.n, 'method':method, 'params':params})+'\n').encode())
        self.f.flush()
        while True:
            line = self.f.readline()
            if not line:
                raise AssertionError('API connection closed')
            result = json.loads(line)
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


def main():
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
    rpc.call('project.create', location=WORK, name='PruebaUI', video={'width':320,'height':180,'rateNum':30,'rateDen':1})
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
    _, transition_search_y = click_label('Buscar', '11-transition-search', min_y=.4)
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
    deadline = time.monotonic()+300
    while time.monotonic()<deadline:
        state = rpc.call('export.status', job=result['job'])
        if state['state'] != 'running':
            assert state['state']=='done', state
            break
        time.sleep(2)
    else:
        raise AssertionError('Export did not complete within 300s')
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
    assert abs(float(probe['format']['duration'])-4)<.1
    assert any(s['codec_type']=='audio' for s in probe['streams'])
    run('ffmpeg','-v','error','-i',str(OUT/'ui-result.mp4'),'-f','null','-')
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
        assert scores[label+'_export_error'] < 10, f'Preview/export disagree: {scores}'
    (OUT/'visual-verification.json').write_text(json.dumps(scores,indent=2))
    (OUT/'PASS.json').write_text(json.dumps({'result':'PASS','scope':'real taps split, effect, transition; saved/reopened; same document exported via engine API at1080p; no Samsung test','actions':LOG},indent=2))


try:
    main()
except Exception:
    shot('FAIL')
    raise
finally:
    (OUT/'actions.json').write_text(json.dumps(LOG,indent=2))
    (OUT/'logcat.txt').write_bytes(run('adb','logcat','-d','-v','threadtime',check=False))
    run('adb','forward','--remove','tcp:7420',check=False)
