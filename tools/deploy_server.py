"""Deploy helper for the Nitrado test server.

Credentials come from the environment: DZ_FTP_HOST, DZ_FTP_USER, DZ_FTP_PASS.

  deploy_server.py mod <local @DynamicSeasons dir>     upload the mod and its bikey, verify by re-download
  deploy_server.py seed <config.json> <state.json> <backup dir>
                                                       back up existing season files, then upload new ones
  deploy_server.py ls <remote dir>                     list a remote directory
  deploy_server.py get <remote file> <local file>      download a file
"""
import ftplib
import hashlib
import io
import os
import sys

BASE = '/dayzstandalone'
MOD_NAME = '@DynamicSeasons'


def connect():
    ftp = ftplib.FTP(os.environ['DZ_FTP_HOST'], timeout=180)
    ftp.login(os.environ['DZ_FTP_USER'], os.environ['DZ_FTP_PASS'])
    return ftp


def sha(data):
    return hashlib.sha256(data).hexdigest().upper()


def ensure_dir(ftp, path):
    current = ''
    for part in path.strip('/').split('/'):
        current += '/' + part
        try:
            ftp.mkd(current)
        except ftplib.error_perm as exc:
            if not str(exc)[:3] in ('550', '521'):
                raise


def download(ftp, remote):
    buf = io.BytesIO()
    ftp.retrbinary('RETR ' + remote, buf.write)
    return buf.getvalue()


def exists(ftp, remote):
    try:
        ftp.size(remote)
        return True
    except ftplib.error_perm:
        return False


def upload_verified(ftp, local, remote):
    with open(local, 'rb') as fh:
        data = fh.read()
    ftp.storbinary('STOR ' + remote, io.BytesIO(data))
    back = download(ftp, remote)
    ok = sha(back) == sha(data)
    print('%s %s %d %s' % ('OK ' if ok else 'BAD', remote, len(data), sha(data)))
    return ok


def cmd_mod(local_mod):
    ftp = connect()
    ok = True
    remote_mod = BASE + '/' + MOD_NAME
    for root, _dirs, files in os.walk(local_mod):
        rel = os.path.relpath(root, local_mod).replace('\\', '/')
        remote_dir = remote_mod if rel == '.' else remote_mod + '/' + rel
        ensure_dir(ftp, remote_dir)
        for name in sorted(files):
            ok &= upload_verified(ftp, os.path.join(root, name), remote_dir + '/' + name)
    keys = os.path.join(local_mod, 'keys')
    ensure_dir(ftp, BASE + '/keys')
    for name in sorted(os.listdir(keys)):
        if name.lower().endswith('.bikey'):
            ok &= upload_verified(ftp, os.path.join(keys, name), BASE + '/keys/' + name)
    ftp.quit()
    return ok


def cmd_seed(config, state, backup_dir):
    ftp = connect()
    remote_dir = BASE + '/config/DynamicSeasons'
    os.makedirs(backup_dir, exist_ok=True)
    for name in ('config.json', 'state.json'):
        remote = remote_dir + '/' + name
        if exists(ftp, remote):
            data = download(ftp, remote)
            with open(os.path.join(backup_dir, name), 'wb') as fh:
                fh.write(data)
            print('backed up existing %s (%d bytes)' % (remote, len(data)))
        else:
            print('no existing %s' % remote)
    ensure_dir(ftp, remote_dir)
    ok = upload_verified(ftp, config, remote_dir + '/config.json')
    ok &= upload_verified(ftp, state, remote_dir + '/state.json')
    ftp.quit()
    return ok


def cmd_ls(remote):
    ftp = connect()
    lines = []
    ftp.retrlines('LIST ' + remote, lines.append)
    for line in lines:
        print(line)
    ftp.quit()
    return True


def cmd_get(remote, local):
    ftp = connect()
    data = download(ftp, remote)
    with open(local, 'wb') as fh:
        fh.write(data)
    print('%s -> %s %d bytes' % (remote, local, len(data)))
    ftp.quit()
    return True


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    command = argv[1]
    if command == 'mod':
        return 0 if cmd_mod(argv[2]) else 1
    if command == 'seed':
        return 0 if cmd_seed(argv[2], argv[3], argv[4]) else 1
    if command == 'ls':
        return 0 if cmd_ls(argv[2]) else 1
    if command == 'get':
        return 0 if cmd_get(argv[2], argv[3]) else 1
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv))
