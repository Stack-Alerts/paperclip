# Rclone credential recovery

Paperclip backups include `rclone.conf` and `rclone-pass` only as encrypted files under `extras/config/rclone/`:

```text
extras/config/rclone/
├── MANIFEST.json
├── rclone.conf.enc
└── rclone-pass.enc
```

The files are encrypted with AES-256-CBC and PBKDF2-HMAC-SHA256 (200,000 iterations). Each ciphertext and its identifying metadata also carries a bootstrap-derived HMAC, which restore verifies before decrypting or replacing a destination. The per-host bootstrap key is independent of the rclone credentials, so it can be used before GDrive access is available. The backup archive and manifest never contain plaintext credential values.

## Before the first backup

Generate the key once on the backup host and store it outside the host and outside GDrive:

```bash
scripts/rclone-credentials-bootstrap.sh
chmod 600 ~/.paperclip/rclone-creds-bootstrap.key
stat -c '%a %n' ~/.paperclip/rclone-creds-bootstrap.key
```

Copy the key to an offline password manager, encrypted removable device, or other operator-controlled store. Do not put it in the backup archive. Keep the key fingerprint from `scripts/rclone-credentials-bootstrap.sh --print` with the recovery record; the fingerprint identifies the key without revealing it.

The bootstrap helper is idempotent. Do not run `--reset` or `--rotate` unless the consequences are understood:

- `--reset` creates a new key and makes existing encrypted credential snapshots unreadable.
- `--rotate` archives the old key and creates a new one; retain the archived key for older snapshots.

## Lost host, bootstrap key available

1. Install Paperclip and copy the original bootstrap key to the expected path on the replacement host:

   ```bash
   install -d -m 700 ~/.paperclip
   install -m 600 /secure/offline-store/rclone-creds-bootstrap.key \\
     ~/.paperclip/rclone-creds-bootstrap.key
   ```

2. Download a backup using an operator-managed path or storage copy. If GDrive is the only copy, obtain the snapshot through the storage operator or another host that still has working rclone credentials; the encrypted subtree is not needed until after the snapshot is downloaded.
3. Restore the payload. The normal `restore-from-drive.sh latest <destination>` flow detects `extras/config/rclone/MANIFEST.json` and restores the credentials after extraction. For a downloaded snapshot, run the helper directly:

   ```bash
   scripts/rclone-credentials-restore.sh /path/to/restore/extras --force
   ```

4. Verify file ownership and permissions without printing contents:

   ```bash
   stat -c '%a %n' ~/.config/rclone/rclone.conf ~/.config/rclone/rclone-pass
   sha256sum ~/.config/rclone/rclone.conf ~/.config/rclone/rclone-pass
   rclone listremotes
   ```

   Both files and their parent directory should be owner-only (`600` files, `700` directory). `rclone listremotes` verifies that the restored config is usable without logging the credential contents.

## Lost host, bootstrap key also lost

Past encrypted credential snapshots cannot be decrypted without the bootstrap key. Do not guess keys or overwrite a working snapshot. On the replacement host:

```bash
scripts/rclone-credentials-bootstrap.sh --reset
```

Then complete fresh rclone OAuth/configuration, recreate `rclone-pass` if the remote uses crypt, and verify the new remote before the next backup:

```bash
rclone listremotes
scripts/rclone-credentials-bootstrap.sh --print
```

Record that older encrypted credential payloads are unrecoverable and retain any database/file portions of those backups separately.

## Host available, bootstrap key lost

The existing live rclone files may still work, but the old encrypted snapshots cannot be recovered. Do not delete or rotate the live credentials as part of this procedure. Complete fresh rclone configuration only if the live files are unavailable, then generate and securely store a new bootstrap key:

```bash
scripts/rclone-credentials-bootstrap.sh --reset
```

The next backup will use the new key. Keep the old encrypted snapshots for their other recovery data, but mark their rclone credential subtree as unavailable.

## Safety checks

- Restore refuses to overwrite an existing destination unless `--force` is explicit.
- A missing `rclone-pass` is reported as a skipped optional file; `rclone.conf` is still packaged.
- Wrong-key or corrupted-ciphertext decryption exits with status `2` and does not install partial plaintext.
- Packaging and restore logs contain sizes and SHA-256 fingerprints only, never secret values.
- Run the synthetic regression fixture before changing the helpers:

  ```bash
  scripts/__tests__/rclone-credentials-roundtrip.sh
  ```
