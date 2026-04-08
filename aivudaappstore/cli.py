from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from aivudaappstore import __version__


@dataclass(frozen=True)
class CommandSpec:
    name: str
    script_relpath: str
    summary: str
    usage: str


COMMANDS = {
    "install": CommandSpec(
        name="install",
        script_relpath="scripts/install_aivudaappstore.sh",
        summary="Install or update the Aivuda AppStore user service.",
        usage="aivudaappstore install",
    ),
    "uninstall": CommandSpec(
        name="uninstall",
        script_relpath="scripts/uninstall_aivudaappstore.sh",
        summary="Uninstall the Aivuda AppStore user service.",
        usage="aivudaappstore uninstall",
    ),
    "start": CommandSpec(
        name="start",
        script_relpath="scripts/_start_aivudaappstore_service.sh",
        summary="Start the Aivuda AppStore systemd user service.",
        usage="aivudaappstore start",
    ),
    "stop": CommandSpec(
        name="stop",
        script_relpath="scripts/_stop_aivudaappstore_service.sh",
        summary="Stop the Aivuda AppStore systemd user service.",
        usage="aivudaappstore stop",
    ),
    "restart": CommandSpec(
        name="restart",
        script_relpath="scripts/_restart_aivudaappstore_service.sh",
        summary="Restart the Aivuda AppStore systemd user service.",
        usage="aivudaappstore restart",
    ),
    "enable-autostart": CommandSpec(
        name="enable-autostart",
        script_relpath="scripts/_enable_autostart_aivudaappstore_service.sh",
        summary="Enable service autostart in user systemd.",
        usage="aivudaappstore enable-autostart",
    ),
    "disable-autostart": CommandSpec(
        name="disable-autostart",
        script_relpath="scripts/_disable_autostart_aivudaappstore_service.sh",
        summary="Disable service autostart in user systemd.",
        usage="aivudaappstore disable-autostart",
    ),
    "run-stack": CommandSpec(
        name="run-stack",
        script_relpath="scripts/_run_aivudaappstore_stack.sh",
        summary="Run the backend and Caddy stack in the foreground.",
        usage="aivudaappstore run-stack [--dev]",
    ),
    "download-caddy": CommandSpec(
        name="download-caddy",
        script_relpath="scripts/_download_caddy.sh",
        summary="Download or install the Caddy binary into the runtime tools directory.",
        usage="aivudaappstore download-caddy [--source PATH_OR_URL] [--output PATH]",
    ),
    "web": CommandSpec(
        name="web",
        script_relpath="scripts/_web_hint.sh",
        summary="Print the Aivuda AppStore web addresses.",
        usage="aivudaappstore web",
    ),
    "status": CommandSpec(
        name="status",
        script_relpath="scripts/_status_aivudaappstore_service.sh",
        summary="Print the web access hints and aivudaappstore.service status.",
        usage="aivudaappstore status",
    ),
}


def _resource_root() -> str:
    package_dir = Path(__file__).resolve().parent
    from_env = os.environ.get("AIVUDAAPPSTORE_PACKAGE_ROOT", "").strip()
    if from_env:
        return str(Path(from_env).expanduser().resolve())
    return str((package_dir / "resources").resolve())


def _script_path(command: CommandSpec) -> str:
    return os.path.join(_resource_root(), command.script_relpath)


def _print_main_help() -> int:
    print("Usage: aivudaappstore [--help] [--version] <command> [args...]")
    print("")
    print("Commands:")
    for command in COMMANDS.values():
        print("  {0:<18} {1}".format(command.name, command.summary))
    print("  version            Print the installed Aivuda AppStore package version.")
    print("")
    print("Run 'aivudaappstore <command> --help' for command-specific usage.")
    return 0


def _print_command_help(command: CommandSpec) -> int:
    print("Usage: {0}".format(command.usage))
    print("")
    print(command.summary)
    print("")
    print("This command delegates to:")
    print("  {0}".format(command.script_relpath))
    return 0


def _run_shell_script(command: CommandSpec, forwarded_args: List[str]) -> int:
    script_path = _script_path(command)
    if not os.path.exists(script_path):
        print("Packaged script not found: {0}".format(script_path), file=sys.stderr)
        return 1

    env = os.environ.copy()
    env["AIVUDAAPPSTORE_VERSION"] = __version__
    env["AIVUDAAPPSTORE_PACKAGE_ROOT"] = _resource_root()
    env["AIVUDAAPPSTORE_CLI_COMMAND"] = command.name

    completed = subprocess.run(["bash", script_path] + forwarded_args, env=env, check=False)
    return completed.returncode


def main(argv: Optional[List[str]] = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)

    if not args:
        return _print_main_help()

    head = args[0]
    if head in {"-h", "--help", "help"}:
        if len(args) == 1:
            return _print_main_help()
        command = COMMANDS.get(args[1])
        if command is None:
            print("Unknown command: {0}".format(args[1]), file=sys.stderr)
            return 2
        return _print_command_help(command)

    if head in {"-V", "--version", "version"}:
        print(__version__)
        return 0

    command = COMMANDS.get(head)
    if command is None:
        print("Unknown command: {0}".format(head), file=sys.stderr)
        print("")
        return _print_main_help()

    forwarded_args = args[1:]
    if any(arg in {"-h", "--help"} for arg in forwarded_args):
        return _print_command_help(command)
    if any(arg in {"-V", "--version"} for arg in forwarded_args):
        print(__version__)
        return 0

    return _run_shell_script(command, forwarded_args)


if __name__ == "__main__":
    raise SystemExit(main())
