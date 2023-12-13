import argparse
import configparser
import json


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--cfg', required=True)
  parser.add_argument('-o', '--output', required=True)
  args = parser.parse_args()

  configp = configparser.ConfigParser()
  configp.read(args.cfg)

  with open(configp.get('slapconsole', 'cert_file')) as f:
    crt = f.read()

  with open(configp.get('slapconsole', 'key_file')) as f:
    key = f.read()

  url = configp.get('slapos', 'master_url')

  with open(args.output, 'w') as f:
    json.dump(
      {
        'client.crt': crt,
        'client.key': key,
        'master-url': url
      }, f, indent=2)


if __name__ == '__main__':
  main()
