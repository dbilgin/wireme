# wireme

`wireme` is a terminal UI for managing WireGuard peers:

- view interface + peer status
- add peers (optionally show QR, optionally save client config)
- show QR for saved client configs
- delete peers (typed confirmation; optionally deletes matching saved client config)

## Requirements

- **python3** (for the TUI)
- **wg** (WireGuard tools)
- **wg-quick** (only needed if you choose “Apply now (wg syncconf)”)
- **ip** (for endpoint guessing)
- **qrencode** (optional; only needed for QR rendering)

## Install (system-wide)

```bash
curl -fsSL https://raw.githubusercontent.com/dbilgin/wireme/master/install.sh | sudo bash
```

This installs:

- `/usr/local/bin/wireme`
- `/usr/local/lib/wireme/wireme/`

## Usage

Run:

```bash
wireme
```

Notes:

- `wireme` reads WireGuard configs from `/etc/wireguard/*.conf`.
- Adding/deleting peers requires **root** (run `sudo wireme`).
- Saved client configs live under `/etc/wireguard/clients/<iface>/`.

## QR codes (optional)

QR rendering uses the `qrencode` command. If it’s not installed, `wireme` will show an error when you try a QR action.

Example install on Debian/Ubuntu:

```bash
sudo apt-get update && sudo apt-get install -y qrencode
```

## Update

Re-run the installer:

```bash
curl -fsSL https://raw.githubusercontent.com/dbilgin/wireme/master/install.sh | sudo bash
```

## Uninstall

```bash
sudo rm -f /usr/local/bin/wireme
sudo rm -rf /usr/local/lib/wireme
```
