import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';
import { spawnSync } from 'node:child_process';
const require = createRequire(import.meta.url);
const vite = join(dirname(require.resolve('vite/package.json')), 'bin/vite.js');
const result = spawnSync(process.execPath, [vite, 'build', '--config', 'vite.local.config.ts'], { stdio: 'inherit' });
process.exit(result.status ?? 1);
