2026-04-29
''''''''''

- Use GNU coreutils instead of Rust reimplementation.

2026-04-25
''''''''''

- Ubuntu 26.04 LTS

2026-04-10
''''''''''

- New package with NotePOD changes to standard Ubuntu.
  It is automatically upgraded, to bring new changes to existing setups.

2026-03-20
''''''''''

- auto-upgrade Ungoogled Chromium (unattended-upgrades)

2026-03-16
''''''''''

- Firefox: preconfigure with some settings from LibreWolf, uBlock Origin
  and a few other extensions
- all snaps are upgraded when generating installer image
- helper tool to deploy re6st & slapos

2026-03-02
''''''''''

- disk encryption: add support for FIDO2 tokens
- disk encryption: stricter password checking

2026-02-24
''''''''''

- autologin at boot time (since the user just entered the disk password, no
  need to reask the user password)
- rework language support
- add ungoogled-chromium
- auto upgrade re6st-node and slapos-node packages

2026-02-20
''''''''''

This is the first version of NotePOD. For now the features are:

- based on Ubuntu 25.10
- full disk encryption (included swap) protected by password
- `re6st-node` and `slapos-node` preinstalled but not configured
