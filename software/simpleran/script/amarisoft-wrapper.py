import asyncio, hashlib, hmac, json, os, shutil, string, subprocess, sys, time, websockets
from slapos.recipe.librecipe import GenericBaseRecipe, generateHashFromFiles

async def websocket_connect(websocket, password):
    data = json.loads(await websocket.recv())
    if password:
        res = hmac.new(
          '{}:{}:{}'.format(data['type'], password, data['name']).encode(),
          msg=data['challenge'].encode(),
          digestmod=hashlib.sha256
        ).hexdigest()
        await websocket.send(f'{{"message":"authenticate", "res": "{res}"}}')
        rsp = await websocket.recv()

async def websocket_get_ssb(uri, password):
    async with websockets.connect(uri, origin='simpleran-sr') as websocket:
        await websocket_connect(websocket, password)
        try:
            await websocket.send(f'{{"message":"config_get"}}')
            nr_cells = json.loads(await websocket.recv())['nr_cells']
            return [nr_cells[k]['ssb_nr_arfcn'] for k in nr_cells]
        except KeyError:
            return []

async def websocket_quit(uri, password, ignore_error=False):
    try:
        async with websockets.connect(uri, origin='simpleran-sr') as websocket:
            await websocket_connect(websocket, password)
            await websocket.send(f'{{"message":"quit"}}')
    except (ConnectionRefusedError, websockets.exceptions.InvalidMessage) as e:
        if not ignore_error:
            raise e

def get_ssb():
    ssb_list = [0, 0]
    for i in range(5):
        try:
            ssb_list = asyncio.run(websocket_get_ssb(options['ws-url'], options.get('ws-password')))
        except ConnectionRefusedError as e:
            time.sleep(0.1)
            continue
        break
    print(f'SSB NR ARFCN list: {", ".join(map(str, ssb_list))}')
    return ssb_list

def publish_ssb(publish, ssb_list):
    # Publish ssb-nr-arfcn
    publish['RADIO.ssb-nr-arfcn'] = ' / '.join(map(str, ssb_list))
    if 'ID.handover-json-export' in publish:
        for i in range(len(ssb_list)):
            publish['ID.handover-json-export'] = \
              publish['ID.handover-json-export'].replace(f'CELL{i}__SSB_NR_ARFCN__', str(ssb_list[i]))

def hash_file_list(file_list):
    h = hashlib.sha256()
    for path in file_list:
        with open(path, 'rb') as f:
            h.update(f.read())
    return h.hexdigest()

def parse_amarisoft_stderr(stderr):
    # Filter out non ascii characters
    amarisoft_error = ''.join(filter(lambda x: x in set(string.printable), stderr))
    if 'no license found' in amarisoft_error:
        amarisoft_error = 'License error: no license found\n' + amarisoft_error.split('\n')[-2]
    return amarisoft_error

amarisoft_error = 'No error'
dry_config_file_list  = options['dry-config-file-list'].split('\n')
amarisoft_service = options['amarisoft-service']
amarisoft_binary = os.path.join(options['amarisoft-directory'], amarisoft_service)
publish = self.buildout['publish-connection-information']

os.environ['AMARISOFT_PATH'] = options['amarisoft-license-dir']

# Check if the generated configuration files have changed
new_hash = hash_file_list(dry_config_file_list)
new_service = f'{amarisoft_service}-service-{new_hash}'
try:
    with open(options['hash-output-file'], 'r') as f:
        previous_hash = f.read()
except FileNotFoundError:
    previous_hash = ''

# Check if any configuration file in running-config-directory is missing
file_missing = False
for path in dry_config_file_list:
    filename = os.path.basename(path)
    if not os.path.exists(os.path.join(options['running-config-directory'], filename)):
        file_missing = True

# List current installed services
service_list = []
for path in os.listdir(options['service-directory']):
    if path.startswith(f'{amarisoft_service}-service-'):
        service_list.append(path)

# Dry run amarisoft to check for any errors
# Always dry run amarisoft even if configuration hasn't changed in case licenses are invalid
proc = subprocess.run([amarisoft_binary, '-d', options['amarisoft-config-file']], timeout=0.3,
  stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, check=False)

if proc.returncode or file_missing or new_hash != previous_hash or new_service not in service_list:

    if proc.returncode:
        print(f'{amarisoft_service} dry run failed')
        amarisoft_error = parse_amarisoft_stderr(proc.stderr)
    else:
        # Write working config files to etc
        for path in dry_config_file_list:
            filename = os.path.basename(path)
            shutil.copyfile(path, os.path.join(options['running-config-directory'], filename))
        # Remove previous installed services
        for path in os.listdir(options['service-directory']):
            if path.startswith('lteenb-service-'):
                os.remove(os.path.join(options['service-directory'], path))
        # Install new service
        for path in os.listdir(options['bin-directory']):
            if path.startswith(f'{amarisoft_service}-service-'):
                shutil.copy(os.path.join(options['bin-directory'], path), os.path.join(
                  options['service-directory'], new_service))

        # Restart amarisoft service
        if new_hash != previous_hash or new_service not in service_list:
            reason = \
              f'{new_hash} != {previous_hash}' if (new_hash != previous_hash) else f'{new_service}  is missing'
            print(f'{reason}, restarting lteenb')

            # Kill previous amarisoft service
            asyncio.run(websocket_quit(options['ws-url'], options.get('ws-password'), ignore_error=True))

            if amarisoft_service == 'lteenb':
                # Start lteenb with dummy driver to get SSB NR ARFCN
                while True:
                    # Retry to kill previous amarisoft service in case it did not succeed before
                    asyncio.run(websocket_quit(options['ws-url'], options.get('ws-password'), ignore_error=True))
                    proc = subprocess.Popen([amarisoft_binary, '-n', options['amarisoft-config-file']],
                      stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    # If previous lteenb has not yet quit, dummy lteenb will fail immediatly
                    # We sleep and retry if that is the case to wait for lteenb to quit
                    try:
                        proc.communicate(timeout=0.2)
                    except subprocess.TimeoutExpired:
                        break
                    time.sleep(0.3)
                ssb_list = get_ssb()
                # Kill dummy lteenb
                asyncio.run(websocket_quit(options['ws-url'], options.get('ws-password')))
                try:
                    proc.communicate(timeout=0.2)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.communicate()
                # Publish ssb-nr-arfcn
                publish_ssb(publish, ssb_list)

            with open(options['hash-output-file'], 'w+') as f:
                f.write(new_hash)

# Check if there are SSB NR ARFCN values to replace
# Ensures SSB NR ARFCN is always published if something went wrong previously
if '__SSB_NR_ARFCN__' in publish.get('RADIO.ssb-nr-arfcn', '') or \
 '__SSB_NR_ARFCN__' in publish.get('ID.handover-json-export', ''):
    ssb_list = get_ssb()
    publish_ssb(publish, ssb_list)

publish['ERROR.amarisoft'] = amarisoft_error
