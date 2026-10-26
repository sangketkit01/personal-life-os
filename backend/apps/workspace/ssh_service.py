"""
SSH engine for Infrastructure Assets (paramiko, agentless).

Zero-Disk Policy: SSH private keys and passwords are decrypted in memory
(io.StringIO) and handed straight to paramiko - nothing is ever written
to temporary files on disk.
"""
import base64
import hashlib
import io
import json
import re
import shlex
import time
from typing import Dict, Any, List, Optional, Tuple

import paramiko
from django.utils import timezone

from apps.storage.encryption import decrypt_token
from .models import InfrastructureAsset, SshAuthType

# Strict allow-list: docker container names/ids only ([a-zA-Z0-9_.-]).
CONTAINER_ID_RE = re.compile(r'^[a-zA-Z0-9_.-]{1,128}$')
DOCKER_ACTIONS = ('start', 'stop', 'restart', 'logs')

# Single round-trip telemetry probe: all seven metrics in ONE exec channel.
PROBE_SECTION_SEP = '===LIFEOS_SECTION==='
PROBE_BATCH_CMD = (
    "cat /proc/uptime 2>/dev/null; echo '===LIFEOS_SECTION==='; "
    "cat /proc/loadavg 2>/dev/null; echo '===LIFEOS_SECTION==='; "
    "nproc 2>/dev/null; echo '===LIFEOS_SECTION==='; "
    "free -m 2>/dev/null | awk 'NR==2{printf \"%s %s\", $3,$2}'; echo '===LIFEOS_SECTION==='; "
    "df -BM / 2>/dev/null | awk 'NR==2{printf \"%s %s %s\", $3,$2,$5}'; echo '===LIFEOS_SECTION==='; "
    "uname -sr 2>/dev/null; echo '===LIFEOS_SECTION==='; "
    "docker ps -a --format '{{json .}}' 2>/dev/null"
)

HEALTH_ONLINE = 'ONLINE'
HEALTH_OFFLINE = 'OFFLINE'
HEALTH_WARNING = 'WARNING'


class SshConnectionError(Exception):
    """Raised when the SSH channel to an asset cannot be established."""


def _load_private_key_from_memory(key_material: str, passphrase: str = '') -> paramiko.PKey:
    """
    Load a paramiko private key from an in-memory string, trying the common
    key families in order. Never writes the key to disk.
    """
    # Normalize Windows CRLF to LF, strip surrounding blank whitespace and
    # guarantee a trailing newline - PEM/OpenSSH parsers reject missing final
    # newlines and stray CR characters.
    normalized_key = key_material.replace('\r\n', '\n').replace('\r', '\n').strip() + '\n'
    key_file = io.StringIO(normalized_key)
    passphrase_bytes = passphrase.encode('utf-8') if passphrase else None
    errors = []
    for key_cls in (paramiko.Ed25519Key, paramiko.RSAKey, paramiko.ECDSAKey):
        key_file.seek(0)
        try:
            return key_cls.from_private_key(key_file, password=passphrase_bytes)
        except paramiko.PasswordRequiredException:
            raise SshConnectionError(
                'SSH private key is passphrase-protected but no passphrase was stored.'
            )
        except paramiko.SSHException as exc:
            errors.append(f'{key_cls.__name__}: {exc}')
    raise SshConnectionError('Could not parse SSH private key. Tried Ed25519/RSA/ECDSA. ' + ' | '.join(errors))


def calculate_key_fingerprint(key: paramiko.PKey) -> str:
    """Calculate the SHA256 base64 fingerprint of an SSH public key."""
    digest = hashlib.sha256(key.asbytes()).digest()
    b64_fp = base64.b64encode(digest).decode('utf-8').rstrip('=')
    return f"SHA256:{b64_fp}"


class AssetHostKeyPolicy(paramiko.MissingHostKeyPolicy):
    """
    Host key verification policy bound to the InfrastructureAsset record:
    - If trusted fingerprint is absent:
        - If accept_new_host_key=True: trust and persist the remote fingerprint.
        - If accept_new_host_key=False: reject with SshConnectionError requiring user confirmation.
    - If trusted fingerprint is present:
        - If matches: allow connection.
        - If mismatch: reject with SshConnectionError (MITM alert). Never auto-accept mismatch.
    """
    def __init__(self, asset: InfrastructureAsset, accept_new_host_key: bool = False):
        self.asset = asset
        self.accept_new_host_key = accept_new_host_key

    def missing_host_key(self, client: paramiko.SSHClient, hostname: str, key: paramiko.PKey):
        remote_fp = calculate_key_fingerprint(key)
        trusted_fp = (self.asset.ssh_host_fingerprint or '').strip()

        if not trusted_fp:
            if self.accept_new_host_key:
                self.asset.ssh_host_fingerprint = remote_fp
                self.asset.save(update_fields=['ssh_host_fingerprint', 'updated_at'])
                client.get_host_keys().add(hostname, key.get_name(), key)
                return
            raise SshConnectionError(
                f"SSH host key for '{hostname}' is not verified. Server fingerprint: {remote_fp}. "
                "Explicit confirmation is required before connecting."
            )

        if remote_fp != trusted_fp:
            raise SshConnectionError(
                f"WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED FOR '{hostname}'! "
                f"Remote host key fingerprint is {remote_fp}, but trusted fingerprint is {trusted_fp}. "
                "Connection aborted to protect against Man-in-the-Middle attacks."
            )

        client.get_host_keys().add(hostname, key.get_name(), key)


def open_ssh_client(
    asset: InfrastructureAsset,
    timeout: int = 10,
    accept_new_host_key: bool = False
) -> paramiko.SSHClient:
    """
    Open an authenticated paramiko SSHClient for the given asset.
    Credentials are decrypted in memory only.
    Strict host key verification enforces stored fingerprint per asset.
    """
    host = (asset.ip_address or '').strip() or (asset.hostname or '').strip()
    if not host:
        raise SshConnectionError('Asset has no IP address or hostname configured.')

    if asset.ssh_auth_type == SshAuthType.NONE:
        raise SshConnectionError('Asset is marked as console-only (no SSH credentials).')

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(
        AssetHostKeyPolicy(asset, accept_new_host_key=accept_new_host_key)
    )

    connect_kwargs = {
        'hostname': host,
        'port': asset.ssh_port or 22,
        'username': (asset.ssh_username or 'root').strip() or 'root',
        'timeout': timeout,
        'allow_agent': False,
        'look_for_keys': False,
    }

    if asset.ssh_auth_type == SshAuthType.PRIVATE_KEY:
        key_material = decrypt_token(asset.ssh_private_key_encrypted)
        if not key_material:
            raise SshConnectionError('Asset is configured for key auth but no private key is stored.')
        passphrase = decrypt_token(asset.ssh_passphrase_encrypted)
        connect_kwargs['pkey'] = _load_private_key_from_memory(key_material, passphrase)
    else:
        password = decrypt_token(asset.ssh_password_encrypted)
        if not password:
            raise SshConnectionError('Asset is configured for password auth but no password is stored.')
        connect_kwargs['password'] = password

    try:
        client.connect(**connect_kwargs)
    except paramiko.AuthenticationException:
        client.close()
        raise SshConnectionError('SSH authentication failed - check username/credentials.')
    except paramiko.SSHException as exc:
        client.close()
        raise SshConnectionError(f'SSH connection failed: {exc}')
    except OSError as exc:
        client.close()
        raise SshConnectionError(f'Cannot reach {host}:{asset.ssh_port or 22} ({exc}).')
    return client


def _run_command(client: paramiko.SSHClient, command: str, timeout: int = 15) -> Tuple[str, str, int]:
    """Execute a single command and return (stdout, stderr, exit_status)."""
    stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
    try:
        out = stdout.read().decode('utf-8', errors='replace')
        err = stderr.read().decode('utf-8', errors='replace')
        exit_status = stdout.channel.recv_exit_status()
    finally:
        stdin.close()
        stdout.close()
        stderr.close()
    return out, err, exit_status


def _format_uptime(seconds: float) -> str:
    seconds = int(seconds)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    if days > 0:
        return f'{days}d {hours}h'
    if hours > 0:
        return f'{hours}h {minutes}m'
    return f'{minutes}m'


def _parse_docker_ps(raw_output: str) -> List[Dict[str, Any]]:
    """Parse `docker ps -a --format '{{json .}}'` output lines into dicts."""
    containers = []
    for line in raw_output.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            containers.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return containers


def probe_server_telemetry(asset: InfrastructureAsset, accept_new_host_key: bool = False) -> Dict[str, Any]:
    """
    Agentless Level-1 probe: uptime, load, memory, disk, kernel and the full
    docker container list via one SSH session. Persists the snapshot on the
    asset (health_status / last_telemetry / last_checked_at) and returns it.
    """
    started = time.monotonic()
    telemetry: Dict[str, Any] = {
        'cpu_pct': None,
        'load_avg': None,
        'ram_used_mb': None,
        'ram_total_mb': None,
        'ram_pct': None,
        'disk_used_gb': None,
        'disk_total_gb': None,
        'disk_pct': None,
        'uptime_seconds': None,
        'uptime_human': None,
        'kernel': '',
        'containers': [],
        'error': None,
    }

    client = None
    try:
        client = open_ssh_client(asset, accept_new_host_key=accept_new_host_key)

        # One batched exec round-trip instead of seven. If the batch marker is
        # absent (e.g. a test mocking per-command responses), fall back to the
        # original individual calls so behavior stays identical.
        batch_out, _, _ = _run_command(client, PROBE_BATCH_CMD, timeout=15)
        if PROBE_SECTION_SEP in batch_out:
            sections = batch_out.split(PROBE_SECTION_SEP)

            def _sec(i):
                return sections[i] if i < len(sections) else ''

            uptime_out = _sec(0)
            load_out = _sec(1)
            nproc_out = _sec(2)
            free_out = _sec(3)
            df_out = _sec(4)
            uname_out = _sec(5)
            docker_out = _sec(6)
            docker_ok = bool(docker_out.strip())
        else:
            uptime_out, _, _ = _run_command(client, 'cat /proc/uptime')
            load_out, _, _ = _run_command(client, 'cat /proc/loadavg')
            nproc_out, _, _ = _run_command(client, 'nproc')
            free_out, _, _ = _run_command(client, "free -m | awk 'NR==2{printf \"%s %s\", $3,$2}'")
            df_out, _, _ = _run_command(client, "df -BM / | awk 'NR==2{printf \"%s %s %s\", $3,$2,$5}'")
            uname_out, _, _ = _run_command(client, 'uname -sr')
            docker_out, _, docker_status = _run_command(client, "docker ps -a --format '{{json .}}' 2>/dev/null")
            docker_ok = docker_status == 0

        parts = uptime_out.split()
        if parts:
            telemetry['uptime_seconds'] = float(parts[0])
            telemetry['uptime_human'] = _format_uptime(float(parts[0]))

        if load_out.split():
            telemetry['load_avg'] = float(load_out.split()[0])

        try:
            nproc = max(1, int(nproc_out.strip()))
        except ValueError:
            nproc = 1

        free_parts = free_out.split()
        if len(free_parts) == 2:
            used_mb, total_mb = float(free_parts[0]), float(free_parts[1])
            telemetry['ram_used_mb'] = used_mb
            telemetry['ram_total_mb'] = total_mb
            telemetry['ram_pct'] = round((used_mb / total_mb) * 100, 1) if total_mb > 0 else None

        df_parts = df_out.split()
        if len(df_parts) == 3:
            used_gb = float(df_parts[0].rstrip('M')) / 1024.0
            total_gb = float(df_parts[1].rstrip('M')) / 1024.0
            telemetry['disk_used_gb'] = round(used_gb, 2)
            telemetry['disk_total_gb'] = round(total_gb, 2)
            telemetry['disk_pct'] = float(df_parts[2].rstrip('%')) if '%' in df_parts[2] else None

        telemetry['kernel'] = uname_out.strip()

        if docker_ok:
            telemetry['containers'] = _parse_docker_ps(docker_out)

        # CPU utilization estimate from 1-minute load average vs core count.
        if telemetry['load_avg'] is not None:
            telemetry['cpu_pct'] = round(min(100.0, (telemetry['load_avg'] / nproc) * 100.0), 1)

    except SshConnectionError as exc:
        telemetry['error'] = str(exc)
        asset.health_status = HEALTH_OFFLINE
    except Exception as exc:  # unexpected transport failure still marks OFFLINE
        telemetry['error'] = f'Unexpected probe failure: {exc}'
        asset.health_status = HEALTH_OFFLINE
    else:
        breached = (
            (telemetry['cpu_pct'] is not None and telemetry['cpu_pct'] >= asset.alert_cpu_threshold)
            or (telemetry['ram_pct'] is not None and telemetry['ram_pct'] >= asset.alert_ram_threshold)
            or (telemetry['disk_pct'] is not None and telemetry['disk_pct'] >= asset.alert_disk_threshold)
        )
        asset.health_status = HEALTH_WARNING if breached else HEALTH_ONLINE
    finally:
        if client is not None:
            client.close()
        telemetry['probe_ms'] = int((time.monotonic() - started) * 1000)
        asset.last_telemetry = telemetry
        asset.last_checked_at = timezone.now()
        asset.save(update_fields=['health_status', 'last_telemetry', 'last_checked_at', 'updated_at'])

    return telemetry


def manage_docker_container(
    asset: InfrastructureAsset,
    container_id: str,
    action: str,
    tail: int = 100,
    accept_new_host_key: bool = False
) -> Dict[str, Any]:
    """
    Level-1 docker management: start/stop/restart a container or fetch its
    logs. container_id is strictly validated to neutralize command injection.
    """
    container_id = str(container_id or '').strip()
    if not CONTAINER_ID_RE.match(container_id):
        raise ValueError('Invalid container identifier.')
    action = str(action or '').strip().lower()
    if action not in DOCKER_ACTIONS:
        raise ValueError(f'Unsupported docker action. Allowed: {", ".join(DOCKER_ACTIONS)}.')
    try:
        tail = max(1, min(int(tail), 1000))
    except (TypeError, ValueError):
        tail = 100

    client = open_ssh_client(asset, accept_new_host_key=accept_new_host_key)
    try:
        if action == 'logs':
            out, err, exit_status = _run_command(
                client, f'docker logs --tail {tail} {container_id} 2>&1', timeout=30
            )
            return {
                'action': action,
                'container_id': container_id,
                'output': out or err,
                'exit_status': exit_status,
                'telemetry': probe_server_telemetry(asset, accept_new_host_key=accept_new_host_key),
            }

        out, err, exit_status = _run_command(client, f'docker {action} {container_id}', timeout=60)
        result = {
            'action': action,
            'container_id': container_id,
            'output': (out + err).strip(),
            'exit_status': exit_status,
            'telemetry': probe_server_telemetry(asset, accept_new_host_key=accept_new_host_key),
        }
        return result
    finally:
        client.close()


def execute_remote_command(
    asset: InfrastructureAsset,
    command: str,
    working_dir: str = '',
    timeout: int = 60,
    accept_new_host_key: bool = False
) -> Dict[str, Any]:
    """
    Level-2 one-shot command execution. working_dir is shell-quoted and
    prefixed via `cd ... &&` so paths with spaces are safe.
    """
    command = str(command or '').strip()
    if not command:
        raise ValueError('Command must not be empty.')
    try:
        timeout = max(1, min(int(timeout), 600))
    except (TypeError, ValueError):
        timeout = 60

    full_command = f'cd {shlex.quote(working_dir)} && {command}' if working_dir.strip() else command

    started = time.monotonic()
    client = open_ssh_client(asset, accept_new_host_key=accept_new_host_key)
    try:
        stdin, stdout, stderr = client.exec_command(full_command, timeout=timeout)
        try:
            out = stdout.read().decode('utf-8', errors='replace')
            err = stderr.read().decode('utf-8', errors='replace')
            exit_status = stdout.channel.recv_exit_status()
        finally:
            stdin.close()
            stdout.close()
            stderr.close()
    finally:
        client.close()

    return {
        'command': full_command,
        'stdout': out,
        'stderr': err,
        'exit_status': exit_status,
        'duration_ms': int((time.monotonic() - started) * 1000),
    }
