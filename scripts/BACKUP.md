# paperclip-btcaaaaa-main backup script

Offsite backup of Paperclip instance data to Google Drive via rclone.
The script is `backup-to-drive.sh` and is launched either by cron
(4-hourly) or manually for a one-shot snapshot.

## Plugin discovery rule

The "stage plugin sources" block in `backup-to-drive.sh` (lines
662-771) auto-discovers every eligible Paperclip plugin rather than
maintaining a hard-coded allowlist.

**Rule:** a directory under `packages/plugins/*/` is an eligible
Paperclip plugin if its `package.json` declares a `paperclipPlugin`
OBJECT that references `manifest` and `worker` paths which resolve to
existing files relative to the plugin root. `ui` is optional.

- Silent skip: `paperclipPlugin` absent or explicitly `null`.
- Hard fail with rc=2: `paperclipPlugin` present but the wrong type, or
  missing required `manifest`/`worker` fields. The error names the
  file and the missing field so the issue is recoverable in one edit.
- Hard fail with rc=3: required path fields declared but the artifact
  doesn't exist on disk (e.g. plugin was added without running
  `pnpm --filter <plugin> build`). The error names the declared path
  and the expected resolved location.

This rule is enforced by an embedded Python validator in the script;
the validator writes its decision to stdout (canonical name + plugin
root) or stderr (FAIL with rc 2/3) and the bash loop acts on the
exit code.

`BACKUP_PLUGIN_NAMES` (optional, default empty) acts as an allowlist
override — when set, only plugins whose directory basename matches
are shipped. The default auto-discovers every eligible plugin, so
adding a new plugin under `packages/plugins/` with a valid
`paperclipPlugin` field requires no script edit.

The change-detection gate at lines 430-435 already scans every
`packages/plugins/*/src/*` and `package.json` without an allowlist
filter, so snapshot invalidation continues to fire correctly when any
plugin's source changes — even ones the old hard-coded list missed.

## Verification

`scripts/tests/test_discover_paperclip_plugins.sh` exercises the
staging block against synthetic fixtures in a `mktemp -d` workspace:

- Valid plugin A (with `ui`) and B (without `ui`) are staged; their
  `src/`, `package.json`, and `dist/` are copied.
- Non-plugins (no field or `paperclipPlugin: null`) are silently
  skipped.
- `node_modules/` and `examples/` fixtures are excluded by the `find`
  filter.
- The `BACKUP_PLUGIN_NAMES=paperclip-fixture-a` override narrows the
  shipped set to just that plugin.
- A malformed entry missing the `manifest` field aborts with rc=2 and
  the stderr message names the missing field.
- A malformed entry whose declared `manifest` path is missing on disk
  aborts with rc=3 and the stderr message names the missing path.
- A malformed entry with `paperclipPlugin: [...]` (array, not object)
  aborts with rc=2.
- Removing the broken fixtures and re-running lets discovery succeed
  again, proving the abort is recoverable.

Run it directly:

```bash
bash /home/sirrus/.paperclip/scripts/tests/test_discover_paperclip_plugins.sh
```

All assertions pass on the current script. Captured run output:

```
=== auto-discover (BACKUP_PLUGIN_NAMES unset, BACKUP_PLUGIN_DISCOVERY_DIRS=fixture) ===
  ok  [shipped set]
  ok  [non-plugins + node_modules + examples all skipped]
  ok  [fixture-a has src/, package.json, dist/ staged]
  ok  [fixture-b has dist/ staged]

=== allowlist override (BACKUP_PLUGIN_NAMES=fixture-a) ===
  ok  [allowlist shipped set]

=== malformed (manifest field missing) aborts with rc=2 ===
  ok  [malformed rc]
  ok  [stderr names the missing manifest field]

=== malformed (declared artifact missing on disk) aborts with rc=3 ===
  ok  [missing-artifact rc]
  ok  [stderr names the missing artifact path]

=== malformed (paperclipPlugin is array) aborts with rc=2 ===
  ok  [wrong-type rc]
  ok  [stderr names the wrong type]

=== auto-recovers once malformed fixtures are removed ===
  ok  [post-recovery shipped set]

ALL DISCOVERY ASSERTIONS PASSED
```
