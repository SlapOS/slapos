#!{{ python_path }}
import json, os, re, shutil, subprocess, sys, tarfile, tempfile
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms
from pathlib import Path
from datetime import datetime
from slapos.libnetworkcache import NetworkcacheClient
from slapos.libnetworkcache import NetworkcacheFilter

def run(cmd, *args, text=True, **kw):
    return subprocess.run(cmd, *args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=text, shell=True, **kw)

def log(s, *args, **kw):
    print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] {s}', *args, **kw)

def chacha20_decrypt_stream(src, dst, key, nonce):
    chunk_size = 1024 * 1024
    decryptor = Cipher(algorithms.ChaCha20(key, nonce), mode=None).decryptor()

    total = 0
    while True:
        chunk = src.read(chunk_size)
        if not chunk:
            break
        dst.write(decryptor.update(chunk))
        total += len(chunk)
    dst.write(decryptor.finalize())
    return total

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
        run(f'sudo -n /opt/amarisoft/setcap {binary} {",".join(cap_list)}', check=True)

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

if len(sys.argv) != 5:
    print("Usage: ./download-amarisoft.py INSTALL_DIR VERSION TIMESTAMP FPGA_VERSION")
    exit()

install_dir = Path(sys.argv[1])
version      = sys.argv[2]
timestamp    = sys.argv[3]
fpga_version = sys.argv[4]
amarisoft_path = install_dir / f'v{version}.{timestamp}'
fpga_path      = install_dir / f'fpga-{fpga_version}.{version}.{timestamp}.bin'

download_amarisoft = not amarisoft_path.is_dir()
download_fpga      = not fpga_path.is_file()

if download_amarisoft or download_fpga:

    key_dir       = Path('/opt/private-key')
    cn            = run('hostname').stdout.strip()
    private_key   = key_dir / f'{cn}.key'
    public_key    = key_dir / f'{cn}.pub'

    if not private_key.is_file() or not public_key.is_file():
        sys.stderr.write(f'Error: {private_key} or {public_key} are not files\n')
        exit(1)

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

    nc = NetworkcacheClient(config)

    meta = [
      f'cn=="{cn}"',
      f'version=="{version}"',
      f'timestamp=="{timestamp}"',
    ]
    identifier = 'key-private:amarisoft'
    data_list = NetworkcacheFilter(meta)(list(nc.select(identifier)))

    if not data_list:
        log("No amarisoft version found")
        exit()

    data = data_list[0]

    log(f'Found Amarisoft version: {version}.{timestamp}')
    log(f'Downloading encrypted key')
    encrypted_key = nc.download(data['sha512']).read()
    log(f'Decrypting key')
    # Decrypt key
    private_symmetric_key = run(f'openssl pkeyutl -decrypt -inkey {key_dir}/{cn}.key',
      text=False, input=encrypted_key).stdout

    # Download new amarisoft version
    meta = [
      f'version=="{version}"',
      f'timestamp=="{timestamp}"',
    ]
    identifier = 'file-private:amarisoft'
    file_data_list = NetworkcacheFilter(meta)(list(nc.select(identifier)))
    # Get Nonce / IV
    nonce = file_data_list[0]['nonce'].encode()
    nonce = run(f'openssl base64 -A -d', text=False, input=nonce).stdout

    if download_amarisoft:

        log(f'Downloading, decrypting and extracting Amarisoft encrypted tar')

        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(f'{tmpdir}/libs')
            src = nc.download(file_data_list[0]['sha512']) # Download from shacache
            reader = DecryptingReader(src, private_symmetric_key, nonce) # Decrypt
            # Extract the main tar.gz
            with tarfile.open(fileobj=reader, mode="r|gz", bufsize=1024 * 1024) as tar:
                for member in tar:
                    # Extract each amarisoft software tar.gz we want to install to tmpdir
                    if member.isfile() and member.name in [
                      f'{version}/lteenb-linux-{version}.tar.gz' ,
                      f'{version}/lteue-linux-{version}.tar.gz'  ,
                      f'{version}/ltemme-linux-{version}.tar.gz' ,
                      f'{version}/ltewww-{version}.tar.gz'       ,
                      f'{version}/trx_sdr-linux-{version}.tar.gz',
                      ]:
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
                for path in [
                  f'{tmpdir}/ltemme-linux-{version}',
                  f'{tmpdir}/lteenb-linux-{version}',
                  f'{tmpdir}/lteue-linux-{version}' ,
                  ]:
                    shutil.copy(f'{tmpdir}/libs/{library_name}', f'{path}/{library_name}')
                os.remove(f'{tmpdir}/libs/{library_name}')

            log(f'Making Amarisoft symlinks')
            os.symlink(f'lteenb-linux-{version}' , f'{tmpdir}/enb'    )
            os.symlink(f'lteue-linux-{version}'  , f'{tmpdir}/ue'     )
            os.symlink(f'ltemme-linux-{version}' , f'{tmpdir}/mme'    )
            os.symlink(f'ltewww-{version}'       , f'{tmpdir}/www'    )
            os.symlink(f'trx_sdr-linux-{version}', f'{tmpdir}/trx_sdr')

            log(f'Copying Amarisoft libraries')
            run(f'cp {tmpdir}/trx_sdr/*.so* {tmpdir}/enb/')
            run(f'cp {tmpdir}/trx_sdr/*.so* {tmpdir}/ue/')

            run(f'mv {tmpdir} {amarisoft_path}')

    if download_fpga:
        # Download fpga
        log(f'Downloading FPGA encrypted bin')
        meta = [
          f'version=="{version}"',
          f'fpga_version=="{fpga_version}"',
          f'timestamp=="{timestamp}"',
        ]
        identifier = 'file-private:fpga'
        fpga_data_list = NetworkcacheFilter(meta)(list(nc.select(identifier)))
        if not fpga_data_list:
            log(f"No FPGA found for version {version}")
        else:
            fpga_version = fpga_data_list[0].get('fpga_version')
            src = nc.download(fpga_data_list[0]['sha512']) # Download from shacache
            reader = DecryptingReader(src, private_symmetric_key, nonce) # Decrypt
            with open(fpga_path, 'wb+') as f:
                shutil.copyfileobj(reader, f)

    if download_amarisoft:
        log(f'New Amarisoft version has been installed in {amarisoft_path}')
    if download_fpga:
        if fpga_data_list:
            log(f'FPGA binary has been installed in {fpga_path}')

else:
    log(f'Version {version}.{timestamp} is already installed')

set_cap(f'{amarisoft_path}/enb/lteenb',      ['cap_sys_nice'])
set_cap(f'{amarisoft_path}/enb/lteenb-avx2', ['cap_sys_nice'])
set_cap(f'{amarisoft_path}/ue/lteue',       ['cap_sys_nice'])
set_cap(f'{amarisoft_path}/ue/lteue-avx2',  ['cap_sys_nice'])
set_cap(f'{amarisoft_path}/mme/lteims',      ['cap_sys_admin', 'cap_net_raw'])
