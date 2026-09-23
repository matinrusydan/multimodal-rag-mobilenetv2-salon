#!/usr/bin/env node
/**
 * freeport.mjs — Bebaskan port sebelum menjalankan service (antisipasi WinError 10048).
 *
 * Usage:
 *   node scripts/freeport.mjs 5000 -- <command...>
 *   node scripts/freeport.mjs 3000 4000 5000 -- <command...>
 *
 * Cara kerja:
 *   1. Untuk setiap port, cari PID yang LISTEN (Windows: netstat; unix: lsof).
 *   2. Matikan proses tsb (taskkill / kill).
 *   3. Jalankan <command...>.
 *
 * Hanya mematikan proses yang MEMEGANG port tsb, bukan proses lain.
 */
import { spawnSync, spawn } from 'node:child_process';
import process from 'node:process';

const argv = process.argv.slice(2);
const sep = argv.indexOf('--');
if (sep === -1) {
  console.error('[freeport] penggunaan: node freeport.mjs <port...> -- <command...>');
  process.exit(2);
}
const ports = argv.slice(0, sep);
const cmd = argv.slice(sep + 1);
if (ports.length === 0 || cmd.length === 0) {
  console.error('[freeport] port atau command kosong');
  process.exit(2);
}

const isWin = process.platform === 'win32';

function pidsOnPort(port) {
  const pids = new Set();
  if (isWin) {
    const r = spawnSync('netstat', ['-ano', '-p', 'TCP'], { encoding: 'utf8' });
    const out = r.stdout || '';
    for (const line of out.split(/\r?\n/)) {
      // contoh: TCP    127.0.0.1:5000    0.0.0.0:0    LISTENING    22236
      const m = line.match(new RegExp(`[:.]${port}\\s+\\S+\\s+LISTENING\\s+(\\d+)`, 'i'));
      if (m) pids.add(m[1]);
    }
  } else {
    const r = spawnSync('lsof', ['-ti', `tcp:${port}`, '-sTCP:LISTEN'], { encoding: 'utf8' });
    for (const pid of (r.stdout || '').split(/\s+/).filter(Boolean)) pids.add(pid);
  }
  return [...pids];
}

function kill(pid) {
  if (isWin) spawnSync('taskkill', ['/F', '/PID', pid], { stdio: 'ignore' });
  else spawnSync('kill', ['-9', pid], { stdio: 'ignore' });
}

for (const port of ports) {
  const pids = pidsOnPort(port);
  if (pids.length === 0) {
    console.log(`[freeport] port ${port} bebas`);
    continue;
  }
  for (const pid of pids) {
    console.log(`[freeport] port ${port} dipakai PID ${pid} -> kill`);
    kill(pid);
  }
}

// beri jeda singkat agar OS melepas socket
spawnSync(process.execPath, ['-e', 'setTimeout(()=>{},700)']);

console.log(`[freeport] menjalankan: ${cmd.join(' ')}`);
const child = spawn(cmd[0], cmd.slice(1), { stdio: 'inherit', shell: isWin });
child.on('exit', (code, signal) => process.exit(code ?? (signal ? 1 : 0)));
child.on('error', (err) => {
  console.error(`[freeport] gagal spawn: ${err.message}`);
  process.exit(1);
});
