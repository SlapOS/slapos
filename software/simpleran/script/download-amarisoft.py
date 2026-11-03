#!/usr/bin/env python3
options = {
  'install-dir': '/srv/slapgrid/slappart12/bin',
  'private-key-dir': '/opt/private-key',
  'version': '2026-09-11',
  'timestamp': '1790341605',
  'fpga-version': '2025-05-16',
}

import json, os, re, shutil, subprocess, sys, tarfile, tempfile
from pathlib import Path
from datetime import datetime
from slapos.libnetworkcache import NetworkcacheClient
from slapos.libnetworkcache import NetworkcacheFilter

def run(cmd, *args, text=True, **kw):
    return subprocess.run(cmd, *args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=text, shell=True, **kw)

def log(s, *args, **kw):
    print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] {s}', *args, **kw)

def chacha20_decrypt_shell(key, nonce, input_file_path, output_file_path):
    run(f'openssl enc -d -chacha20 -K {key} -iv {nonce} -nosalt -in {input_file_path} -out {output_file_path}')

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


def check_cap(path, binary, cap_list):
    current_cap = run(f'getcap {path}/{binary}').stdout
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

def set_cap(path, binary, cap_list):
    run(f'patchelf --set-rpath {path} {path}/{binary} && \
          setcap {",".join(cap_list)}=+pe {path}/{binary}', check=True)

install_dir = Path(options['install-dir'])
version      = options['version']
timestamp    = options['timestamp']
fpga_version = options['fpga-version']
amarisoft_path = f'{install_dir}/v{version}.{timestamp}'
fpga_path      = f'{install_dir}/fpga-{fpga_version}.{version}.{timestamp}.bin'

download_amarisoft = not amarisoft_path.is_file()
download_fpga      = not fpga_path.is_file()

if download_amarisoft or download_fpga:

    key_dir       = Path(options['private-key-dir'])
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
      'version=="{version}"',
      'timestamp=="{timestamp}"',
    ]
    identifier = 'key-private:amarisoft'
    data_list = NetworkcacheFilter(meta)(list(nc.select(identifier)))
    
    if not data_list:
        print("No amarisoft version found")
        exit()
    
    data = data_list[0]
    
    log(f'Found Amarisoft version: {version}.{timestamp}')
    log(f'Downloading encrypted key')
    encrypted_key = nc.download(data['sha512']).read()
    log(f'Decrypting key')
    # Decrypt key
    private_symmetric_key = run(f'openssl pkeyutl -decrypt -inkey {key_dir}/{cn}.key',
      text=False, input=encrypted_key).stdout
    private_symmetric_key = run(f'od -An -v -tx1 -', text=False, input=private_symmetric_key).stdout.decode()
    private_symmetric_key = private_symmetric_key.replace(' ', '').replace('\n', '')

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
    nonce = run(f'od -An -v -tx1 -', text=False, input=nonce).stdout.decode()
    nonce = nonce.replace(' ', '').replace('\n', '')

    if download_amarisoft:
        # Download encrypted amarisoft tar
        log(f'Downloading Amarisoft encrypted tar')
        log(f'Decrypting Amarisoft encrypted tar')

        with tempfile.TemporaryFile() as amarisoft_encrypted_tar:
            #shutil.copyfileobj(src, amarisoft_encrypted_tar)

        with nc.download(file_data_list[0]['sha512']) as src:

            # Decrypt amarisoft tar

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

            cipher = Cipher(algorithms.ChaCha20(private_symmetric_key, nonce), mode=None)
            return cipher.decryptor().update(amarisoft_encrypted_tar)

            chacha20_decrypt_shell(private_symmetric_key, nonce,
              amarisoft_encrypted_tar,
              f'{amarisoft_dir}/amarisoft.tar.gz')

        os.makedirs(amarisoft_dir / version, exist_ok=True)
        run(f'rm -rf {amarisoft_dir}/_{version}')
        os.makedirs(amarisoft_dir / f'_{version}', exist_ok=True)

        log(f'Extracting Amarisoft tar files')
        with tarfile.open(f'{amarisoft_dir}/amarisoft.tar.gz') as f:
            f.extractall(amarisoft_dir)
        with tarfile.open(f'{amarisoft_dir}/{version}/lteenb-linux-{version}.tar.gz') as f:
            f.extractall(f'{amarisoft_dir}/_{version}')
        with tarfile.open(f'{amarisoft_dir}/{version}/lteue-linux-{version}.tar.gz') as f:
            f.extractall(f'{amarisoft_dir}/_{version}')
        with tarfile.open(f'{amarisoft_dir}/{version}/ltemme-linux-{version}.tar.gz') as f:
            f.extractall(f'{amarisoft_dir}/_{version}')
        with tarfile.open(f'{amarisoft_dir}/{version}/ltewww-{version}.tar.gz') as f:
            f.extractall(f'{amarisoft_dir}/_{version}')
        with tarfile.open(f'{amarisoft_dir}/{version}/trx_sdr-linux-{version}.tar.gz') as f:
            f.extractall(f'{amarisoft_dir}/_{version}')

        log(f'Making Amarisoft symlinks')
        os.symlink(f'lteenb-linux-{version}', f'{amarisoft_dir}/_{version}/enb')
        os.symlink(f'lteue-linux-{version}', f'{amarisoft_dir}/_{version}/ue')
        os.symlink(f'ltemme-linux-{version}', f'{amarisoft_dir}/_{version}/mme')
        os.symlink(f'ltewww-{version}', f'{amarisoft_dir}/_{version}/www')
        os.symlink(f'trx_sdr-linux-{version}', f'{amarisoft_dir}/_{version}/trx_sdr')

        log(f'Copying Amarisoft libraries')
        run(f'cp {amarisoft_dir}/_{version}/trx_sdr/*.so* {amarisoft_dir}/_{version}/enb/')
        run(f'cp {amarisoft_dir}/_{version}/trx_sdr/*.so* {amarisoft_dir}/_{version}/ue/')
        run(f'cp {amarisoft_dir}/{version}/libs/*.so* {amarisoft_dir}/_{version}/mme/')
        run(f'cp {amarisoft_dir}/{version}/libs/linux/*.so* {amarisoft_dir}/_{version}/mme/')
        run(f'cp {amarisoft_dir}/{version}/libs/*.so* {amarisoft_dir}/_{version}/enb/')
        run(f'cp {amarisoft_dir}/{version}/libs/*.so* {amarisoft_dir}/_{version}/ue/')
        run(f'cp {amarisoft_dir}/{version}/libs/linux/*.so* {amarisoft_dir}/_{version}/enb/')
        run(f'cp {amarisoft_dir}/{version}/libs/linux/*.so* {amarisoft_dir}/_{version}/ue/')
        run(f'mv {amarisoft_dir}/_{version} {amarisoft_dir}/v{version}.{timestamp}')
        run(f'rm -rf {amarisoft_dir}/{version}')

        def set_cap(path, binary, cap_list):
            if run(f'getcap {path}/{binary}' + ''.join(f' | grep -q {cap}' for cap in cap_list),
              check=False).returncode:
                run(f'patchelf --set-rpath {path} {path}/{binary} && \
                      setcap {",".join(cap_list)}=+pe {path}/{binary}')

        install_dir = f'{amarisoft_dir}/v{version}.{timestamp}'
        set_cap(f'{install_dir}/enb', 'lteenb',      ['cap_sys_nice'])
        set_cap(f'{install_dir}/enb', 'lteenb-avx2', ['cap_sys_nice'])
        set_cap(f'{install_dir}/ue',  'lteue',       ['cap_sys_nice'])
        set_cap(f'{install_dir}/ue',  'lteue-avx2',  ['cap_sys_nice'])
        set_cap(f'{install_dir}/mme', 'lteims',      ['cap_sys_admin', 'cap_net_raw'])

    if download_fpga:
        # Download fpga
        log(f'Downloading FPGA encrypted bin')
        meta = [
          f'version=="{version}"',
          f'timestamp=="{timestamp}"',
        ]
        identifier = 'file-private:fpga'
        fpga_data_list = NetworkcacheFilter(meta)(list(nc.select(identifier)))
        if not fpga_data_list:
            print(f"No FPGA found for version {version}")
        else:
            fpga_version = fpga_data_list[0].get('fpga_version')
            # Download encrypted FPGA bin
            with open(f'{amarisoft_dir}/download/fpga.bin.enc', 'wb+') as f:
                shutil.copyfileobj(nc.download(fpga_data_list[0]['sha512']),
                    getattr(f, 'buffer', f)) # Py3
            # Decrypt FPGA bin
            log(f'Decrypting FPGA encrypted bin')
            chacha20_decrypt_shell(private_symmetric_key, nonce,
              f'{amarisoft_dir}/download/fpga.bin.enc',
              f'{amarisoft_dir}/fpga-{fpga_version}.{version}.{timestamp}.bin')

    if download_amarisoft:
        log(f'New Amarisoft version has been installed in {amarisoft_dir}/v{version}.{timestamp}')
    if download_fpga:
        if fpga_data_list:
            log(f'FPGA binary has been installed in {amarisoft_dir}/fpga-{fpga_version}.{version}.{timestamp}.bin')

else:
    log(f'Version {version}.{timestamp} is already installed')

run(f'rm -rf {amarisoft_dir}/download')
run(f'rm -rf {amarisoft_dir}/amarisoft.tar.gz')
