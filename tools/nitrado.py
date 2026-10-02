"""Nitrado game server helper for the DayZ test server.

The API token comes from the environment: DZ_NITRADO_TOKEN; the service id from DZ_NITRADO_SERVICE.

  nitrado.py status            server status, players online, mods
  nitrado.py restart <message> restart the game server (only call with 0 players online)
  nitrado.py stop <message>    stop the game server (only call with 0 players online), e.g. to replace a PBO the
                               running server keeps open
"""
import json
import os
import sys
import urllib.parse
import urllib.request

API = 'https://api.nitrado.net/services/%s/gameservers'


def request(path='', method='GET', data=None):
    url = API % os.environ['DZ_NITRADO_SERVICE'] + path
    body = None
    if data is not None:
        body = urllib.parse.urlencode(data).encode('utf-8')
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header('Authorization', 'Bearer ' + os.environ['DZ_NITRADO_TOKEN'])
    req.add_header('Accept', 'application/json')
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode('utf-8'))


def cmd_status():
    data = request()
    gs = data['data']['gameserver']
    query = gs.get('query') or {}
    print(json.dumps({
        'status': gs.get('status'),
        'players': query.get('player_current'),
        'player_max': query.get('player_max'),
        'server_name': query.get('server_name'),
        'version': query.get('version'),
        'game_version': gs.get('game_specific', {}).get('update_status'),
        'last_status_change': gs.get('last_status_change'),
        'mods_param': (gs.get('settings') or {}).get('config', {}).get('mods') if isinstance(gs.get('settings'), dict) else None,
    }, indent=1))
    return 0


def cmd_restart(message):
    data = request('/restart', 'POST', {'message': message, 'restart_message': ''})
    print(json.dumps(data))
    return 0 if data.get('status') == 'success' else 1


def cmd_stop(message):
    data = request('/stop', 'POST', {'message': message, 'stop_message': ''})
    print(json.dumps(data))
    return 0 if data.get('status') == 'success' else 1


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    if argv[1] == 'status':
        return cmd_status()
    if argv[1] == 'restart':
        return cmd_restart(' '.join(argv[2:]) or 'restart')
    if argv[1] == 'stop':
        return cmd_stop(' '.join(argv[2:]) or 'stop')
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv))
