#!/usr/bin/env bash
# Structural checks only; these do not replace Android playback/export tests.
set -euo pipefail
apk=${1:?usage: verify-apk.sh /absolute/path/to/candidate.apk}
sdk=${ANDROID_HOME:?set ANDROID_HOME}
ndk=${ANDROID_NDK_HOME:?set ANDROID_NDK_HOME}
build_tools=$(find "$sdk/build-tools" -mindepth 1 -maxdepth 1 -type d | sort -V | tail -1)
readelf="$ndk/toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-readelf"
"$build_tools/apksigner" verify --verbose --print-certs "$apk"
"$build_tools/zipalign" -c -P 16 4 "$apk"
badging=$("$build_tools/aapt" dump badging "$apk")
printf '%s\n' "$badging"
[[ "$badging" == *"package: name='cl.kokumix.editpop.concatcandidate'"* ]]
[[ "$badging" == *"sdkVersion:'26'"* ]]
[[ "$badging" == *"targetSdkVersion:'35'"* ]]
python3 - "$apk" "$readelf" <<'PY'
import pathlib, subprocess, sys, tempfile, zipfile
with zipfile.ZipFile(sys.argv[1]) as apk, tempfile.TemporaryDirectory() as tmp:
    libraries = [n for n in apk.namelist() if n.startswith('lib/') and n.endswith('.so')]
    assert 'lib/arm64-v8a/libconcat_android.so' in libraries, libraries
    for name in libraries:
        assert name.startswith('lib/arm64-v8a/'), f'Unexpected ABI: {name}'
        target = pathlib.Path(tmp) / pathlib.Path(name).name
        target.write_bytes(apk.read(name))
        headers = subprocess.check_output([sys.argv[2], '-lW', str(target)], text=True)
        loads = [line.split() for line in headers.splitlines() if line.strip().startswith('LOAD ')]
        assert loads, f'No LOAD segments: {name}'
        assert all(int(row[-1], 16) >= 16384 for row in loads), f'Not 16 KiB aligned: {name}'
        print('ELF 16 KiB PASS:', name)
print('Structural checks PASS; Android runtime validation still required.')
PY
sha256sum "$apk"
