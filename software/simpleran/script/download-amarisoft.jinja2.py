#!{{ python_path }}
import json, os, re, shutil, subprocess, sys, tarfile, tempfile
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms
from pathlib import Path
from datetime import datetime
import time
from slapos.libnetworkcache import NetworkcacheClient
from slapos.libnetworkcache import NetworkcacheFilter

def run(cmd, *args, text=True, **kw):
    return subprocess.run(cmd, *args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=text, shell=True, **kw)

def log(s, *args, **kw):
    print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] {s}', *args, **kw)

def check_cap(binary, cap_list):
    current_cap = run(f'getcap {binary}').stdout
    if not current_cap:
        return False
    current_cap = current_cap.split(' ')[1].split('=')
    current_cap_list = current_cap[0].split(',')
    if ''.join(sorted(current_cap[1].strip())) != 'ep':
        return False
    for cap in cap_list:
        if cap not in current_cap_list:
            return False
    return True

def set_cap(binary, cap_list):
    if not check_cap(binary, cap_list):
        log(f'Setting capabilities: {(binary, cap_list)}')
        run(f'sudo -n /opt/simpleran/setcap {binary} {",".join(cap_list)}', check=True)

class DecryptingReader:
    # File-like object that decrypts a ChaCha20 stream on the fly
    def __init__(self, src, key, nonce):
        self.src = src
        self.decryptor = Cipher(algorithms.ChaCha20(key, nonce), mode=None).decryptor()
        self.total = 0
        self.finalized = False

    def read(self, size=-1):
        chunk = self.src.read(size)
        if chunk:
            self.total += len(chunk)
            return self.decryptor.update(chunk)
        if not self.finalized:
            self.finalized = True
            return self.decryptor.finalize()  # b"" for ChaCha20, but keeps it correct
        return b""

def read_timestamp(file_path):
    try:
        with open(file_path, 'r') as f:
            return int(f.read())
    except FileNotFoundError as e:
        return 0
def write_timestamp(file_path, value):
    with open(file_path, 'w+') as f:
        f.write(str(value))


config = {
    'download-cache-url': 'http://shacache.nxdcdn.com',
    'download-dir-url': 'http://shadir.nxdcdn.com',
    'signature-certificate-list': """\
      -----BEGIN CERTIFICATE-----
      MIIEDTCCAnWgAwIBAgIUOPXvdYH461MtYKJFh4uf9ANwn5AwDQYJKoZIhvcNAQEL
      BQAwFTETMBEGA1UEAwwKUmFwaWRTcGFjZTAgFw0yNDA0MTkxMjU0MjNaGA8yMTIy
      MTExMjEyNTQyM1owFTETMBEGA1UEAwwKUmFwaWRTcGFjZTCCAaIwDQYJKoZIhvcN
      AQEBBQADggGPADCCAYoCggGBAObATKTWgX/3mvapLlrFrlTybAzX2NQqSmjeMrfZ
      v/rkGGQzUPVugJ7J8TxDIpaxanDBI0+uIlluGDCVcDh0+jV0xzDOKYGckZqfxcXC
      k4RHxIAx2+Z+Y3DCY0QlzEfAyBmsV7U5Xhq6JAcgIIZdc9Fa/lsXJbwgNTQ9F/mx
      DfCbN0x/MnAdRHnIWvIhKY3NWEtBPdQvrKAiBYwxXuRE2MYivPHUMWicdAobvVi9
      JbXavkmvAQ7lVwOHnRa1I8H+C50RywMdKiW9r5pMlkwu9kdes5a4mVo2wRwoRFNQ
      cVh8yHoOg9PNpB5otOjAMazTwZXKVDUxC03LHsBGgEM6y3rtE5fFajvvT0N6/0jR
      zJQ+cXNadjevLs9xA94d3VLBZtY1Od9nkyKvZNzu047e/9RGI8lI0eRpbSAWCnE+
      p0qDHYaTeT90+Iot/femp+ZG0wNVUNoBkw4jIyatsXRkgFrEVO9chL6FtXgdJH3H
      wwus3RT5malA5UZafJTTNrhpyQIDAQABo1MwUTAdBgNVHQ4EFgQUW6DVpr2gLhrr
      0vj1o28lBncj8jowHwYDVR0jBBgwFoAUW6DVpr2gLhrr0vj1o28lBncj8jowDwYD
      VR0TAQH/BAUwAwEB/zANBgkqhkiG9w0BAQsFAAOCAYEAOgi2NdYRlR7WfNtuUVoq
      Yacmmefy9S3si5/hTI0pHuHxAVPYyAYJZJy60bnjxphUF+m5FvErweFVPpkJaUvg
      hht23dXUcyYMukDjG2VvJjFcIbfIE9WZFhofN8hGI9PjEFOb98kqexYlCmTN48nP
      2EaQ6HC3ZZ6PqKdhCRdWa6MeHSy7UNK+9VKLKbe40sZJRvvgTIazHgb+t+r+qhXi
      D9nkcfvvV7BfclKflYrLNLiTcwg8J/gcI2IMbu3lTZyQrYbBCKwxQZGzQfeX1LCV
      P26M6mP/wWlo7DrHof/FdJ+Qdr8gUhH59y6vNsofzy4P0oC8GcwcTam7o6FJMC5l
      QVWI8zm7G64UGKJBKMoNiP25t1uZzDaJucQAd+4ovsjHctgvcJj8JKzQovIcly+r
      PGHKeoTr8UBhoZZxYQTiOO8OK/F0GFfP9OsXoyFp+527X9tezUk28gzmoi7nuaSt
      qYacPjDsKHmV1RfQFweSMk57RYN4NRJuHhl1OvY8FafK
      -----END CERTIFICATE-----\
    """
}

if len(sys.argv) != 7:
    print("Usage: ./download-amarisoft.py INSTALL_DIR VERSION TIMESTAMP FPGA_VERSION SDR100 SOFTWARE_TYPE")
    exit()

install_dir = Path(sys.argv[1])
version      = sys.argv[2]
revision     = sys.argv[3]
fpga_version = sys.argv[4]
sdr100       = sys.argv[5] == "1"
product      = \
  {"core-network": "ltemme", "enb": "lteenb", "enb-gnb": "lteenb", "gnb": "lteenb", "ue": "lteue"}[sys.argv[6]]
amarisoft_path = install_dir / f'{version}.{revision}'
fpga_path      = install_dir / f'fpga-{fpga_version}.{version}.{revision}'
amarisoft_license_dir = install_dir / 'amarisoft-licenses'
os.makedirs(amarisoft_license_dir, exist_ok=True)

# Check current Amarisoft licenses
license_list = [license for license in \
  os.listdir(amarisoft_license_dir) if re.match(product + r"-[0-9]*.[0-9]{4}-[0-9]{2}-[0-9]{2}.key", license)]
try:
    last_license_timestamp, last_license_expiration = sorted([license.split(f"{product}-")[1].split('.license')[0].split('.') for license in license_list])[0]
except IndexError:
    last_license_timestamp, last_license_expiration = 0, '0000-00-00'
download_license       = last_license_expiration < version

# Check current Amarisoft binary and FPGA timestamp
current_amarisoft_timestamp = read_timestamp(amarisoft_path / 'timestamp')
current_fpga_timestamp      = read_timestamp(fpga_path      / 'timestamp')
# Check last download time to limit queries to shacache
amarisoft_download_time = read_timestamp(amarisoft_path / 'download_time')
fpga_download_time      = read_timestamp(fpga_path      / 'download_time')

# Limit queries to shacache, wait 1 hour if Amarisoft has already been downloaded
check_amarisoft = True
check_fpga      = True
if amarisoft_path.is_dir():
    check_amarisoft = (time.time() - amarisoft_download_time) > 60 * 60
if fpga_path.is_dir():
    check_fpga      = (time.time() - fpga_download_time     ) > 60 * 60
    
if check_amarisoft or check_fpga or download_license:

    key_dir       = Path('/opt/private-key')
    cn            = run('hostname').stdout.strip()
    private_key   = key_dir / f'{cn}.key'
    public_key    = key_dir / f'{cn}.pub'

    if not private_key.is_file() or not public_key.is_file():
        sys.stderr.write(f'Error: {private_key} or {public_key} are not files\n')
        exit(1)

    nc = NetworkcacheClient(config)

    if download_license:
        log(f'Check for Amarisoft licenses')
        # Download new amarisoft licenses
        meta = [
          f'cn=="{cn}"',
          f'timestamp>>"{last_license_timestamp}"',
          f'expiration>="{version}"',
        ]
        license_data_list = NetworkcacheFilter(meta)(list(nc.select(f'key-private:{product}')))
        if license_data_list:
            license_expiration = license_data_list[0].get('expiration')
            license_timestamp  = license_data_list[0].get('timestamp')
            encrypted_amarisoft_license = nc.download(license_data_list[0]['sha512']).read()
            log(f'Decrypting Amarisoft license')
            amarisoft_license = run(f'openssl pkeyutl -decrypt -inkey {key_dir}/{cn}.key',
              text=False, input=encrypted_amarisoft_license).stdout
            license_path = amarisoft_license_dir / f'{product}-{license_timestamp}.{license_expiration}.key'
            with open(license_path, 'wb+') as f:
                f.write(amarisoft_license)
        else:
            # Backwards compatibility when key is in /opt/amarisoft/.amarisoft and not in shacache
            opt_license_path = f'/opt/amarisoft/.amarisoft/{product}.key'
            license_timestamp = int(time.time())
            try:
                with open(opt_license_path, 'r') as f:
                    f.seek(260)
                    for l in f:
                        if l.startswith('version='):
                            license_expiration = l.split('=')[1].strip()
                if license_expiration > last_license_expiration:
                    license_path = amarisoft_license_dir / f'{product}-{license_timestamp}.{license_expiration}.key'
                    with open(opt_license_path, 'rb') as opt_license:
                        with open(license_path, 'wb+') as f:
                            f.write(opt_license.read())
            except FileNotFoundError as e:
                pass

    if check_amarisoft or check_fpga:

        flavour = "unpatched" if sdr100 else "patched"
        meta = [
          f'cn=="{cn}"',
          f'version=="{version}"',
          f'revision=="{revision}"',
          f'flavour=="{flavour}"',
          f'timestamp>>"{current_amarisoft_timestamp}"',
        ]
        key_data_list = NetworkcacheFilter(meta)(list(nc.select('key-private:amarisoft')))
        meta = [
          f'fpga_version=="{fpga_version}"',
          f'version=="{version}"',
          f'revision=="{revision}"',
          f'flavour=="{flavour}"',
          f'timestamp>>"{current_fpga_timestamp}"',
        ]
        fpga_data_list = NetworkcacheFilter(meta)(list(nc.select('file-private:fpga')))

        if key_data_list or fpga_data_list:

            key_data = key_data_list[0]

            log(f'Found Amarisoft version: {version}.{revision}')
            log(f'Downloading encrypted key')
            encrypted_key = nc.download(key_data['sha512']).read()
            log(f'Decrypting key')
            # Decrypt key
            private_symmetric_key = run(f'openssl pkeyutl -decrypt -inkey {key_dir}/{cn}.key',
              text=False, input=encrypted_key).stdout

            # Download new amarisoft version
            meta = [
              f'version=="{version}"',
              f'revision=="{revision}"',
              f'flavour=="{flavour}"',
              f'timestamp>>"0"',
            ]
            amarisoft_data_list = NetworkcacheFilter(meta)(list(nc.select('file-private:amarisoft')))
            amarisoft_timestamp = int(amarisoft_data_list[0]['timestamp'])
            # Get Nonce / IV
            nonce = amarisoft_data_list[0]['nonce'].encode()
            nonce = run(f'openssl base64 -A -d', text=False, input=nonce).stdout

            if key_data_list:

                log(f'Downloading, decrypting and extracting Amarisoft encrypted tar')

                with tempfile.TemporaryDirectory() as tmpdir:
                    os.makedirs(f'{tmpdir}/libs')
                    src = nc.download(amarisoft_data_list[0]['sha512']) # Download from shacache
                    reader = DecryptingReader(src, private_symmetric_key, nonce) # Decrypt
                    # Extract the main tar.gz
                    with tarfile.open(fileobj=reader, mode="r|gz", bufsize=1024 * 1024) as tar:
                        for member in tar:
                            # Extract each amarisoft software tar.gz we want to install to tmpdir
                            if product == "ltemme":
                                product_list = [f'{version}/ltemme-linux-{version}.tar.gz']
                            elif product in ["lteenb", "lteue"]:
                                product_list = [
                                  f'{version}/{product}-linux-{version}.tar.gz' ,
                                  f'{version}/ltewww-{version}.tar.gz'       ,
                                  f'{version}/trx_sdr-linux-{version}.tar.gz',
                                ]
                            if member.isfile() and member.name in product_list:
                                fobj = tar.extractfile(member)
                                with tarfile.open(fileobj=fobj) as subtar:
                                    for submember in subtar:
                                        if submember.isfile():
                                            subtar.extract(submember, path=tmpdir, filter="data")
                            if member.isfile() and member.name.startswith(f'{version}/libs/linux/') and \
                             '.so' in member.name: 
                                filename = os.path.basename(member.name)
                                with open(f'{tmpdir}/libs/{filename}', 'wb+') as f:
                                    shutil.copyfileobj(tar.extractfile(member), f)

                    for library_name in os.listdir(f'{tmpdir}/libs'):
                        shutil.copy(f'{tmpdir}/libs/{library_name}', f'{tmpdir}/{product}-linux-{version}/{library_name}')
                        os.remove(f'{tmpdir}/libs/{library_name}')

                    log(f'Making Amarisoft symlinks')
                    if product == "ltemme":
                        os.symlink(f'ltemme-linux-{version}'   , f'{tmpdir}/mme'          )
                    elif product in ["lteenb", "lteue"]:
                        os.symlink(f'{product}-linux-{version}', f'{tmpdir}/{product[3:]}')
                        os.symlink(f'ltewww-{version}'         , f'{tmpdir}/www'          )
                        os.symlink(f'trx_sdr-linux-{version}'  , f'{tmpdir}/trx_sdr'      )

                    if product in ["lteenb", "lteue"]:
                        log(f'Copying Amarisoft libraries')
                        run(f'cp {tmpdir}/trx_sdr/*.so* {tmpdir}/{product[3:]}/')

                    write_timestamp(f'{tmpdir}/timestamp', amarisoft_timestamp)
                    write_timestamp(f'{tmpdir}/download_time', int(time.time()))
                    shutil.rmtree(amarisoft_path, ignore_errors=True) 
                    run(f'sudo -n /opt/simpleran/init-sdr {tmpdir} FORCE')
                    shutil.move(tmpdir, amarisoft_path)


            if fpga_data_list:
                log(f'Downloading FPGA encrypted bin')
                fpga_timestamp = int(fpga_data_list[0]['timestamp'])
                src = nc.download(fpga_data_list[0]['sha512']) # Download from shacache
                reader = DecryptingReader(src, private_symmetric_key, nonce) # Decrypt
                with tempfile.TemporaryDirectory() as tmpdir:
                    with open(f'{tmpdir}/fpga.bin', 'wb+') as f:
                        shutil.copyfileobj(reader, f)
                    write_timestamp(f'{tmpdir}/timestamp', fpga_timestamp)
                    write_timestamp(f'{tmpdir}/download_time', int(time.time()))
                    shutil.rmtree(fpga_path, ignore_errors=True) 
                    shutil.move(tmpdir, fpga_path)

            if amarisoft_data_list:
                log(f'New Amarisoft version has been installed in {amarisoft_path} '\
                    f'(timestamp: {amarisoft_timestamp})')
            if fpga_data_list:
                log(f'FPGA binary has been installed in {fpga_path} (timestamp: {fpga_timestamp})')

if product == "lteenb":
    set_cap(f'{amarisoft_path}/enb/lteenb',      ['cap_sys_nice'])
    set_cap(f'{amarisoft_path}/enb/lteenb-avx2', ['cap_sys_nice'])
elif product == "lteue":
    set_cap(f'{amarisoft_path}/ue/lteue',        ['cap_sys_nice'])
    set_cap(f'{amarisoft_path}/ue/lteue-avx2',   ['cap_sys_nice'])
elif product == "ltemme":
    set_cap(f'{amarisoft_path}/mme/lteims',      ['cap_sys_admin', 'cap_net_raw'])
