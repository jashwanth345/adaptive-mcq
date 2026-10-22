// Explicitly synthetic acceptance fixture, never used by normal application startup.
import { spawn } from 'node:child_process';
import { createInterface } from 'node:readline';
import { seedAttemptFixture } from './attempt-fixture.mjs';
const child = spawn(process.env.TEST_PYTHON, ['-m', 'deployment.native_seed_bridge'], { windowsHide: true, stdio: ['pipe', 'pipe', 'inherit'] });
let next = 0;
const pending = new Map();
createInterface({ input: child.stdout }).on('line', line => {
  const item = JSON.parse(line), callback = pending.get(item.id); pending.delete(item.id);
  item.error ? callback.reject(new Error(item.error)) : callback.resolve(item.result);
});
child.on('exit', () => { for (const callback of pending.values()) callback.reject(new Error('Native fixture bridge exited')); });
const call = payload => new Promise((resolve, reject) => { const id = ++next; pending.set(id, {resolve,reject}); child.stdin.write(JSON.stringify({ id, ...payload })+'\n'); });
try {
  const teacher = await call({op:'teacher'});
  await seedAttemptFixture({query:(sql,params)=>call({sql,params}),exec:sql=>call({sql})}, teacher.teacher, teacher.hash, document=>call({op:'pdf',document}));
  console.log('Synthetic native classroom fixture prepared. Not real AI evidence.');
} finally { child.stdin.end(); }
