#!/usr/bin/env python3
import json, os, re, shutil, subprocess, sys, tarfile
from pathlib import Path
from datetime import datetime
from slapos.libnetworkcache import NetworkcacheClient
from slapos.libnetworkcache import NetworkcacheFilter

def run(cmd, *args, text=True, **kw):
    return subprocess.run(cmd, *args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=text, shell=True, **kw)

def log(s, *args, **kw):
    print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] {s}', *args, **kw)

def chacha20_decrypt_shell(key, nonce, input_file_path, output_file_path):
    print(repr((key, nonce, input_file_path, output_file_path)))
    run(f'openssl enc -d -chacha20 -K {key} -iv {nonce} -nosalt -in {input_file_path} -out {output_file_path}')

amarisoft_dir = Path('/opt/amarisoft')
shacache_cfg  = amarisoft_dir / 'shacache.cfg'
key_dir       = Path('/opt/private-key')
cn            = run('hostname').stdout.strip()
private_key   = key_dir / f'{cn}.key'
public_key    = key_dir / f'{cn}.pub'

if not private_key.is_file() or not public_key.is_file():
    sys.stderr.write(f'Error: {private_key} or {public_key} are not files\n')
    exit(1)

run(f'rm -rf {amarisoft_dir}/download')
os.makedirs(amarisoft_dir / 'download', exist_ok=True)

amarisoft_dir_file_list = os.listdir(amarisoft_dir)
installed_fpga_list = [file for file in amarisoft_dir_file_list if re.match(r"fpga-[0-9]{4}-[0-9]{2}-[0-9]{2}.[0-9]{4}-[0-9]{2}-[0-9]{2}.[0-9]*.bin", file)]
try:
    installed_amarisoft_list = sorted(filter(lambda x: re.match(r"v[0-9]{4}-[0-9]{2}-[0-9]{2}", x),
                                amarisoft_dir_file_list))
except (FileNotFoundError, IndexError):
    installed_amarisoft_list = []

log(f'Current Amarisoft version installed are {", ".join(installed_amarisoft_list)}')
log(f'Current FPGA binaries installed are {", ".join(installed_fpga_list)}')

shacache_file = open(shacache_cfg, 'r')
nc = NetworkcacheClient(shacache_file)

meta = [
  f'cn=="{cn}"',
  'timestamp>="0"',
]
identifier = 'key-private:amarisoft'
data_list = NetworkcacheFilter(meta)(list(nc.select(identifier)))

if not data_list:
    print("No amarisoft version found")
    exit()

for data in sorted(data_list, key=lambda x:x["version"])[-5:]:

    version   = data['version']
    timestamp = data['timestamp']

    log(f'Found Amarisoft version: {version}.{timestamp}')
    
    download_amarisoft = f'v{version}.{timestamp}' not in installed_amarisoft_list
    download_fpga      = f'{version}.{timestamp}'  not in ''.join(installed_fpga_list)
    if download_amarisoft or download_fpga:

        log(f'Downloading encrypted key')
        encrypted_key = nc.download(data['sha512']).read()
        log(f'Decrypting key')
        # Decrypt key
        private_symmetric_key = run(f'openssl pkeyutl -decrypt -inkey /opt/private-key/{cn}.key',
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
            with open(f'{amarisoft_dir}/download/amarisoft.tar.gz.enc', 'wb+') as f:
                shutil.copyfileobj(nc.download(file_data_list[0]['sha512']),
                    getattr(f, 'buffer', f)) # Py3
            # Decrypt amarisoft tar
            log(f'Decrypting Amarisoft encrypted tar')
            chacha20_decrypt_shell(private_symmetric_key, nonce,
              f'{amarisoft_dir}/download/amarisoft.tar.gz.enc',
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
