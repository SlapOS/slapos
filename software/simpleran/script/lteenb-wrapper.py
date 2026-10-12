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

# Check if config files have changed
h = hashlib.sha256()
for path in config_file_list:
    with open(path, 'rb') as f:
        h.update(f.read())
new_hash = h.hexdigest()
try:
    with open(options['hash-output-file'], 'r') as f:
        previous_hash = f.read()
except FileNotFoundError:
    previous_hash = ''

if new_hash != previous_hash:
    with open(options['hash-output-file'], 'w+') as f:
        f.write(new_hash)

file_missing = False
for path in config_file_list:
    filename = os.path.basename(path)
    if not os.path.exists(os.path.join(options['config-directory'], filename)):
        file_missing = True

# Dry run lteenb to check config errors
import subprocess
os.environ['AMARISOFT_PATH'] = options['amarisoft-license-dir']
out = subprocess.run([
  os.path.join(options['enb-directory'], 'lteenb'),
  "-d",
  options['enb-config-file']], stderr=subprocess.PIPE, text=True, check=False)

if out.returncode or file_missing or new_hash != previous_hash:
    if out.returncode:
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
                shutil.copy(os.path.join(options['bin-directory'], path), os.path.join(options['service-directory'], 'lteenb-service-' + new_hash))

    if new_hash != previous_hash and not out.returncode:
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
        asyncio.run(quit_enb(options['ws-url'], options['ws-password']))
        self.buildout['publish-connection-information']['RADIO.ssb-nr-arfcn'] = ' / '.join(map(str, ssb_list))

self.buildout['publish-connection-information']['ERROR.amarisoft'] = error
