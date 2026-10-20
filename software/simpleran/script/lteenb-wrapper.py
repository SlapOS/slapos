import asyncio, hashlib, hmac, json, os, shutil, string, sys, time, websockets

publish = self.buildout['publish-connection-information']
promise = self.buildout['check-configuration-error.py']

async def connect(websocket, password):
    data = json.loads(await websocket.recv())
    res = hmac.new(
      "{}:{}:{}".format(data['type'], password, data['name']).encode(),
      msg=data['challenge'].encode(),
      digestmod=hashlib.sha256
    ).hexdigest()
    await websocket.send(f'{{"message":"authenticate", "res": "{res}"}}')
    rsp = await websocket.recv()

async def get_ssb(uri, password):
    async with websockets.connect(uri, origin="simpleran-sr") as websocket:
        await connect(websocket, password)
        try:
            await websocket.send(f'{{"message":"config_get"}}')
            nr_cells = json.loads(await websocket.recv())['nr_cells']
            return [nr_cells[k]['ssb_nr_arfcn'] for k in nr_cells]
        except KeyError:
            return []

async def quit_enb(uri, password, ignore_error=False):
    try:
        async with websockets.connect(uri, origin="simpleran-sr") as websocket:
            await connect(websocket, password)
            await websocket.send(f'{{"message":"quit"}}')
    except ConnectionRefusedError as e:
        if not ignore_error:
            raise e

error = "No error"
config_file_list = options['config-file-list'].split('\n')

# Check if the generated configuration files have changed
h = hashlib.sha256()
for path in config_file_list:
    with open(path, 'rb') as f:
        h.update(f.read())
new_hash = h.hexdigest()
new_service = f'lteenb-service-{new_hash}'
try:
    with open(options['hash-output-file'], 'r') as f:
        previous_hash = f.read()
except FileNotFoundError:
    previous_hash = ''

# Check if any configuration file in config-directory is missing
file_missing = False
for path in config_file_list:
    filename = os.path.basename(path)
    if not os.path.exists(os.path.join(options['config-directory'], filename)):
        file_missing = True

# List current installed services
service_list = []
for path in os.listdir(options['service-directory']):
    if path.startswith('lteenb-service-'):
        service_list.append(path)

# Dry run lteenb to check for any errors
# We always dry run lteenb even if configuration hasn't changed
# in case licenses are invalid
import subprocess
os.environ['AMARISOFT_PATH'] = options['amarisoft-license-dir']
out = subprocess.run([
  os.path.join(options['enb-directory'], 'lteenb'),
  "-d",
  options['enb-config-file']], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, check=False)

if out.returncode or file_missing or new_hash != previous_hash or new_service not in service_list:
    if out.returncode:
        print("lteenb dry run failed")
        # Filter out non ascii characters
        error = ''.join(filter(lambda x: x in set(string.printable), out.stderr))
        if 'no license found' in error:
            error = 'License error: no license found\n' + error.split('\n')[-2]
        promise['config-error'] = ', '.join([error] + promise.get('config-error', '').split(', '))
    else:
        # Write working config files to etc
        for path in config_file_list:
            filename = os.path.basename(path)
            shutil.copyfile(path, os.path.join(options['config-directory'], filename))
        for path in os.listdir(options['service-directory']):
            if path.startswith('lteenb-service-'):
                os.remove(os.path.join(options['service-directory'], path))
        for path in os.listdir(options['bin-directory']):
            if path.startswith('lteenb-service-'):
                shutil.copy(os.path.join(options['bin-directory'], path), os.path.join(
                  options['service-directory'], 'lteenb-service-' + new_hash))

        if new_hash != previous_hash or new_service not in service_list:
            reason = \
              f'{new_hash} != {previous_hash}' if (new_hash != previous_hash) else f'{new_service}  is missing'
            print(f'{reason}, restarting lteenb')
            asyncio.run(quit_enb(options['ws-url'], options['ws-password'], ignore_error=True))
            while True:
                # Start lteenb with dummy driver to get SSB NR ARFCN
                out = subprocess.Popen([
                  os.path.join(options['enb-directory'], 'lteenb'),
                  "-n",
                  options['enb-config-file']])
                # If previous lteenb has not yet quit, dummy lteenb will fail immediatly
                # We sleep and retry if that is the case to wait for lteenb to quit
                try:
                    out.communicate(timeout=0.2)
                except subprocess.TimeoutExpired:
                    break
                time.sleep(1)
            ssb_list = asyncio.run(get_ssb(options['ws-url'], options['ws-password']))
            print(f'SSB NR ARFCN list: {", ".join(map(str, ssb_list))}')
            asyncio.run(quit_enb(options['ws-url'], options['ws-password']))
            publish['RADIO.ssb-nr-arfcn'] = ' / '.join(map(str, ssb_list))
            if 'ID.handover-json-export' in publish:
                for i in range(len(ssb_list)):
                    publish['ID.handover-json-export'] = \
                      publish['ID.handover-json-export'].replace(f'CELL{i}_SSB_NR_ARFCN', str(ssb_list[i]))
            with open(options['hash-output-file'], 'w+') as f:
                f.write(new_hash)

publish['ERROR.amarisoft'] = error
