# Aivuda AppStore

Aivuda AppStore manages the applications used by aivudaOS.

`aivudaappstore` is the packaged Python distribution of Aivuda AppStore. After installation it provides a unified CLI and stores all runtime data under `${HOME}/aivudaAppStore_ws`.

## Install

Install from PyPI or from a wheel:

```bash
pip install aivudaappstore
# or
pip install aivudaappstore-0.3.0.devYYYYMMDDNN-py3-none-any.whl
```

It is recommended to ensure your user-local bin directory is in `PATH`:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

## First Start

Run the install command once to prepare runtime dependencies, download Caddy, and create the user-level systemd service:

```bash
aivudaappstore install
```

During installation you will be prompted for:

- `APPSTORE_PUBLIC_HTTPS_HOST`: public IP for the cloud server deploying aivudaappstore;
- `APPSTORE_PRIVATE_HTTPS_HOST`: NAT IP for the cloud server deploying aivudaappstore.

The default runtime workspace is:

- `$HOME/aivudaAppStore_ws/data`
- `$HOME/aivudaAppStore_ws/config`
- `$HOME/aivudaAppStore_ws/.tools`
- `$HOME/aivudaAppStore_ws/samples`

## Usage

Common commands:

```bash
aivudaappstore --help
aivudaappstore --version
aivudaappstore install
aivudaappstore web
aivudaappstore status
aivudaappstore start
aivudaappstore stop
aivudaappstore restart
aivudaappstore enable-autostart
aivudaappstore disable-autostart
aivudaappstore download-caddy
aivudaappstore uninstall
```

To print the current web addresses:

```bash
aivudaappstore web
# or
aivudaappstore status
```

Default ports:

- Admin UI: `https://<private-host>:8543`
- Public store: `https://<public-host>:8580`
- Internal backend: `127.0.0.1:9001`

## Build From Source

```bash
git clone https://gitee.com/buaa_iooda/aivudaAppStore.git --recurse-submodules
cd aivudaAppStore
git submodule update --init --recursive
pip install -e .
# pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -e .  # use pypi mirror for build
```

Build wheel and sdist locally:

```bash
cd aivudaappstore/resources/ui
npm install
npm run build
cd ../../..
AIVUDAAPPSTORE_BUILD_SEQ=01 python -m build
```

The wheel includes only `aivudaappstore/resources/ui/dist`, while the sdist keeps the frontend source and excludes `dist` and `node_modules`.

For development details, see [README_dev.md](README_dev.md).
