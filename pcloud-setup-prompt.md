# pCloud WebDAV Mount — Setup Guide

This document explains how to configure pCloud storage via WebDAV for any project, and how it was used in the **noise-filter** project as a real-world example.

---

## Part 1: Generic pCloud WebDAV Setup

### Overview

pCloud provides WebDAV access at `https://webdav.pcloud.com`. This is the most reliable way to mount pCloud on Linux (the official FUSE binary `pcloudcc` may fail to connect). WebDAV via `davfs2` is battle-tested and works consistently.

### Prerequisites

| Requirement | Notes |
|---|---|
| pCloud account | Username (email) and password |
| `davfs2` package | `sudo apt-get install davfs2` (Debian/Ubuntu) |
| Mount point directory | e.g., `/mnt/pcloud` |
| Password access | Via 1Password, env var, or interactive prompt |

### Manual Mount

```bash
echo "$PASSWORD" | sudo mount.davfs \
  -o username="your@email.com",rw,_netdev,fsname=pCloud \
  https://webdav.pcloud.com \
  /mnt/pcloud
```

Replace `your@email.com` and `/mnt/pcloud` with your account and desired mount path.

### Persisting the Mount (fstab)

Add to `/etc/fstab`:

```
https://webdav.pcloud.com /mnt/pcloud davfs user,noauto,uid=$(id -u),gid=$(id -g),file_mode=600,dir_mode=700 0 0
```

Users mount with: `mount /mnt/pcloud`

For password-less mounting, add credentials to `~/.davfs2/secrets`:

```
https://webdav.pcloud.com your@email.com <password>
```

### Automount on Boot (optional)

Change `noauto` to `auto` in fstab, or add the mount command to a systemd service/rc.local.

### Troubleshooting

| Symptom | Likely Fix |
|---|---|
| `mount.davfs: mount failed` | Check network, credentials, and that `/mnt/pcloud` exists |
| `pcloudcc` FUSE binary fails | Skip it — use WebDAV/davfs2 instead (more reliable) |
| Permission denied on mount | Ensure `uid`/`gid` options match your user |
| Slow transfers | WebDAV has overhead; acceptable for moderate file sizes |

---

## Part 2: How pCloud Was Used in noise-filter

### Project Context

[noise-filter](https://github.com/anomalyco/noise-filter) is an audio processing tool that applies noise reduction (highpass, afftdn, anlmdn, compressor, equalizer, lowpass) and extracts vocals/instrumental stems. It has both a Python CLI/TUI and a standalone bash script.

### Why pCloud Was Needed

The project uses large video test files (~194 MB and ~801 MB) for E2E testing. These files are too large to check into git (`movie-samples/` is gitignored). pCloud provides shared remote storage for these assets, accessible from any machine the project runs on.

### Actual Setup Used

| Detail | Value |
|---|---|
| Account | `guillermo@digitalcrushlabs.com` |
| Mount point | `/mnt/pcloud` |
| Storage | 1.3 TB total, ~61% used |
| Credentials | 1Password (`op` CLI) |
| Test audio directory | `/mnt/pcloud/My Music/` |

### How It Integrates

- **E2E tests** reference audio files on the pCloud mount to test the `enhance-voice` script and `noise-filter` CLI with real audio data.
- **CI-independent**: the mount exists on the development machine only; CI uses mock/synthetic audio files instead.
- **Multi-machine**: the same mount command works on any Linux machine with `davfs2` installed — just ensure credentials are available.

### Quick-Start for a New Project

If you want to use pCloud the same way:

1. Install `davfs2` on each machine.
2. Create a mount point (`sudo mkdir -p /mnt/pcloud`).
3. Mount with the command in Part 1 using your pCloud credentials.
4. Store large test assets, datasets, or shared binaries on the mount.
5. Reference files via the mount path in your tests or scripts.
6. Gitignore the local path to keep repos small.
