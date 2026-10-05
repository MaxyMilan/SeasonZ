"""Run offline Blender review renders in parallel, then compose their sheets."""

import argparse
from collections import deque
import csv
import os
from pathlib import Path
import re
import subprocess
import sys
import time


TOOLS = Path(__file__).resolve().parent
PROJECT = TOOLS.parent
WORKSPACE = PROJECT.parent.parent
BLENDER = TOOLS / 'ext/blender-4.5.9-windows-x64/blender.exe'
DEFAULT_LOGS = WORKSPACE / 'dayz-mission-audit/seasonz-mvp-20261004/craft_logs'


def local_path(value):
    path = Path(value).resolve()
    if not path.is_relative_to(WORKSPACE):
        raise ValueError(f'Path is outside workspace: {path}')
    return path


def read_models(log_dir):
    latest = {}
    paths = sorted(log_dir.glob('craft_*.log'))
    if not paths:
        raise ValueError(f'No craft_*.log files in {log_dir}')
    for path in paths:
        # Snapshot complete rows only: craft workers may still be appending.
        lines = path.read_bytes().split(b'\n')[:-1]
        for number, raw in enumerate(lines, 1):
            fields = raw.decode('utf-8', errors='replace').rstrip('\r').split('\t')
            if fields == ['name', 'shape', 'result', 'stats', 'secs']:
                continue
            if len(fields) != 5:
                print(f'WARNING: skipping malformed row {path.name}:{number}', flush=True)
                continue
            name, shape, result, _, _ = fields
            if not re.fullmatch(r'[A-Za-z0-9_-]+', name):
                raise ValueError(f'Invalid model name: {name!r}')
            # Same deterministic last-row convention as craft_all.py.
            latest[name] = (name, shape, result)
    return {name: row for name, row in latest.items() if row[2].startswith('ok')}


def tail(path):
    with path.open(encoding='utf-8', errors='replace') as stream:
        return ''.join(deque(stream, maxlen=12)).rstrip()


def run(args):
    src, out_dir, log_dir = map(local_path, (args.szbake, args.out, args.logs))
    if not src.is_dir():
        raise ValueError(f'Missing szbake directory: {src}')
    for required in (BLENDER, TOOLS / 'render_check.py', TOOLS / 'render_comp.py'):
        if not required.is_file():
            raise ValueError(f'Missing required file: {required}')
    models = read_models(log_dir)
    if args.only is not None:
        only = [name.strip() for name in args.only.split(',')]
        if not all(only) or len(set(only)) != len(only):
            raise ValueError('--only requires distinct, nonempty model names')
        unknown = sorted(set(only) - models.keys())
        if unknown:
            raise ValueError('No successful craft result for: ' + ', '.join(unknown))
        models = {name: models[name] for name in only}
    names = sorted(models)
    if not names:
        raise ValueError('No models with a craft result starting with ok')
    if out_dir == src or out_dir in src.parents:
        raise ValueError('Output directory must not contain the input directory')
    logs = local_path(out_dir / '_logs')
    logs.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    for key, suffix in [('BLENDER_USER_CONFIG', 'config'), ('BLENDER_USER_SCRIPTS', 'scripts'),
                        ('BLENDER_USER_DATAFILES', 'data'), ('BLENDER_USER_EXTENSIONS', 'ext'),
                        ('TEMP', 'tmp'), ('TMP', 'tmp')]:
        directory = local_path(TOOLS / 'ext/bhome' / suffix)
        directory.mkdir(parents=True, exist_ok=True)
        env[key] = str(directory)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    chunks = [names[i:i + args.chunk] for i in range(0, len(names), args.chunk)]
    chunk_logs = [local_path(logs / f'chunk_{i}.txt') for i in range(len(chunks))]
    index_path = local_path(out_dir / 'index.csv')
    comp_log = local_path(logs / 'compose.txt')
    # Validate destinations, including existing symlinks, before starting Blender.
    for path in out_dir.glob('_tile_*.png'):
        local_path(path)
    for path in out_dir.glob('OFF_*.jpg'):
        local_path(path)
    for name in names:
        local_path(out_dir / f'OFF_{name}.jpg')
        for k, var in enumerate((4, 4, 2, 7)):
            local_path(out_dir / f'_tile_{name}_{k}_v{var}.png')
    active = {}
    next_chunk = completed = completed_models = 0
    errors = []
    started = time.monotonic()
    last_report = started
    print(f'Rendering {len(names)} models in {len(chunks)} chunks; up to {args.jobs} workers', flush=True)
    try:
        while next_chunk < len(chunks) or active:
            while next_chunk < len(chunks) and len(active) < args.jobs:
                i = next_chunk
                command = [str(BLENDER), '-b', '--factory-startup', '--python-exit-code', '1',
                           '--python', str(TOOLS / 'render_check.py'), '--', str(src),
                           str(out_dir), ','.join(chunks[i])]
                stream = chunk_logs[i].open('wb')
                try:
                    worker = subprocess.Popen(command, cwd=PROJECT, env=env,
                                              stdout=stream, stderr=subprocess.STDOUT)
                except BaseException:
                    stream.close()
                    raise
                active[i] = (worker, stream)
                next_chunk += 1
                print(f'Start chunk {i}: {", ".join(chunks[i])}', flush=True)
            for i, (worker, stream) in list(active.items()):
                code = worker.poll()
                if code is None:
                    continue
                stream.close()
                del active[i]
                completed += 1
                completed_models += len(chunks[i])
                if code:
                    errors.append(f'Chunk {i} exited with {code}: {chunk_logs[i]}')
                print(f'Finished chunk {i} (exit {code}); {completed}/{len(chunks)} chunks; '
                      f'{completed_models}/{len(names)} models processed; '
                      f'{time.monotonic() - started:.0f}s elapsed', flush=True)
            if time.monotonic() - last_report >= 15:
                print(f'Progress: {completed}/{len(chunks)} chunks finished; '
                      f'{len(active)} workers active; {time.monotonic() - started:.0f}s elapsed', flush=True)
                last_report = time.monotonic()
            if active:
                time.sleep(0.25)
    finally:
        # Only stop processes launched by this runner, including on Ctrl+C.
        for worker, _ in active.values():
            if worker.poll() is None:
                worker.terminate()
        for worker, stream in active.values():
            try:
                worker.wait(timeout=10)
            except subprocess.TimeoutExpired:
                worker.kill()
                worker.wait()
            stream.close()
    incomplete = []
    for name in names:
        if any(not (out_dir / f'_tile_{name}_{k}_v{var}.png').is_file()
               for k, var in enumerate((4, 4, 2, 7))):
            incomplete.append(name)
    if incomplete:
        errors.append('Incomplete current tile sets: ' + ', '.join(incomplete))
    print('All Blender workers stopped; composing sheets once.', flush=True)
    with comp_log.open('wb') as stream:
        composed = subprocess.run([sys.executable, str(TOOLS / 'render_comp.py'), str(out_dir)],
                                  cwd=PROJECT, env=env, stdout=stream, stderr=subprocess.STDOUT)
    if composed.returncode:
        errors.append(f'Composition exited with {composed.returncode}: {comp_log}')
        print(tail(comp_log), flush=True)
    missing = [name for name in names if not (out_dir / f'OFF_{name}.jpg').is_file()]
    with index_path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(('name', 'shape', 'result', 'sheet path'))
        for name in names:
            writer.writerow((*models[name], str(out_dir / f'OFF_{name}.jpg')))
    print('Missing OFF sheets: ' + (', '.join(missing) if missing else 'none'), flush=True)
    for i, chunk in enumerate(chunks):
        affected = sorted(set(chunk) & set(missing + incomplete))
        if affected:
            print(f'Chunk {i} log tail ({", ".join(affected)}):\n{tail(chunk_logs[i])}', flush=True)
    for message in errors:
        print(f'ERROR: {message}', file=sys.stderr, flush=True)
    print(f'Index: {index_path}; {time.monotonic() - started:.0f}s elapsed', flush=True)
    return 1 if errors or missing else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('szbake', help='Directory containing szbake exports')
    parser.add_argument('out', help='Directory for review sheets')
    parser.add_argument('--jobs', type=int, default=12)
    parser.add_argument('--only', help='Comma-separated model names')
    parser.add_argument('--chunk', type=int, default=8)
    parser.add_argument('--logs', default=str(DEFAULT_LOGS))
    args = parser.parse_args()
    if args.jobs < 1 or args.chunk < 1:
        parser.error('--jobs and --chunk must be at least 1')
    try:
        return run(args)
    except KeyboardInterrupt:
        print('\nInterrupted; runner workers stopped.', file=sys.stderr)
        return 130
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
