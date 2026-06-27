#!/usr/bin/env node
/**
 * Guard against dual globals.css files (BTCAAAAA-31091).
 * Ensures only one of packages/web-ui/{app,src/app}/globals.css exists.
 * Prevents the half-shipped CSS-token migration pattern.
 *
 * Canonical source: packages/web-ui/app/globals.css
 */

// eslint-disable-next-line @typescript-eslint/no-require-imports
const fs = require('fs');
// eslint-disable-next-line @typescript-eslint/no-require-imports
const path = require('path');

const appGlobals = path.resolve(__dirname, '../app/globals.css');
const srcAppGlobals = path.resolve(__dirname, '../src/app/globals.css');

const appExists = fs.existsSync(appGlobals);
const srcAppExists = fs.existsSync(srcAppGlobals);

if (appExists && srcAppExists) {
  console.error('\n❌ GUARD VIOLATION: Dual globals.css files detected!');
  console.error('   Found: packages/web-ui/app/globals.css');
  console.error('   Found: packages/web-ui/src/app/globals.css');
  console.error('\n   Canonical source: packages/web-ui/app/globals.css');
  console.error('   Please delete: packages/web-ui/src/app/globals.css (and the full src/app/ if empty)');
  console.error('\n   Background: BTCAAAAA-31091 — dual files cause half-shipped CSS token migrations.\n');
  process.exit(1);
}

if (!appExists && !srcAppExists) {
  console.error('\n⚠️  WARNING: No globals.css found in web-ui!');
  console.error('   Expected: packages/web-ui/app/globals.css\n');
  process.exit(1);
}

const active = appExists ? 'app/globals.css' : 'src/app/globals.css';
console.log(`✓ Single globals.css guard OK (active: ${active})`);
process.exit(0);
