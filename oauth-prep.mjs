// Step 1 of 2 — generates the PKCE values + Etsy authorization URL.
// Run: node oauth-prep.mjs
import crypto from 'crypto';
import fs from 'fs';

function loadEnv(path) {
  const out = {};
  for (const line of fs.readFileSync(path, 'utf8').split('\n')) {
    const m = line.match(/^([A-Z_]+)=(.*)$/);
    if (m) out[m[1]] = m[2].trim();
  }
  return out;
}

function base64url(buf) {
  return buf.toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

const env = loadEnv('.env.local');
const KEYSTRING = env.ETSY_KEYSTRING;
const REDIRECT_URI = env.ETSY_REDIRECT_URI;

if (!KEYSTRING || !REDIRECT_URI) {
  console.error('Missing ETSY_KEYSTRING or ETSY_REDIRECT_URI in .env.local');
  process.exit(1);
}

const verifier = base64url(crypto.randomBytes(64));
const challenge = base64url(crypto.createHash('sha256').update(verifier).digest());
const state = base64url(crypto.randomBytes(16));

fs.writeFileSync('.oauth-session.json', JSON.stringify({ verifier, state, redirect_uri: REDIRECT_URI, client_id: KEYSTRING }, null, 2));

const authUrl = new URL('https://www.etsy.com/oauth/connect');
authUrl.searchParams.set('response_type', 'code');
authUrl.searchParams.set('redirect_uri', REDIRECT_URI);
authUrl.searchParams.set('scope', 'listings_r shops_r');
authUrl.searchParams.set('client_id', KEYSTRING);
authUrl.searchParams.set('state', state);
authUrl.searchParams.set('code_challenge', challenge);
authUrl.searchParams.set('code_challenge_method', 'S256');

console.log('AUTH_URL:' + authUrl.toString());
