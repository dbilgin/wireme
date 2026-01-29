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

Mutual exclusion:

- If `wiremec` is already installed, `install.sh` will refuse to install `wireme`.

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
curl -fsSL https://raw.githubusercontent.com/dbilgin/wireme/master/uninstall.sh | sudo bash
```

---

## wiremec (client)

`wiremec` is the client companion tool:

- import a client WireGuard config
- save it to `/etc/wireguard/<iface>.conf` (backup if exists)
- bring the interface up/down via `wg-quick`
- show status via `wg show`

### Install (client)

```bash
curl -fsSL https://raw.githubusercontent.com/dbilgin/wireme/master/installc.sh | sudo bash
```

Mutual exclusion:

- If `wireme` is already installed, `installc.sh` will refuse to install `wiremec`.

### Usage

```bash
wiremec
```

### Update (client)

Re-run the installer:

```bash
curl -fsSL https://raw.githubusercontent.com/dbilgin/wireme/master/installc.sh | sudo bash
```

### Uninstall (client)

```bash
curl -fsSL https://raw.githubusercontent.com/dbilgin/wireme/master/uninstallc.sh | sudo bash
```
