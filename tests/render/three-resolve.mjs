// Lets node --test import 'three' and 'three/addons/…' from the library (ES modules ignore NODE_PATH; the browser
// pages use an importmap for the same names). Used for the styles' film kits (specs/022).
import { register } from 'node:module';
import { pathToFileURL } from 'node:url';
import path from 'node:path';
const lib = path.resolve(import.meta.dirname, '../../lib/lemo-opuscar/node_modules/three');
const hook = `
const BASE = ${JSON.stringify(pathToFileURL(lib).href)};
export async function resolve(spec, ctx, next) {
  if (spec === 'three') return next(BASE + '/build/three.module.js', ctx);
  if (spec.startsWith('three/addons/')) return next(BASE + '/examples/jsm/' + spec.slice(13), ctx);
  return next(spec, ctx);
}`;
register('data:text/javascript,' + encodeURIComponent(hook));
