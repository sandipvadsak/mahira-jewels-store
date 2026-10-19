// Step 2 of 2 — waits on the local redirect_uri for Etsy's OAuth callback,
// exchanges the code for tokens, saves them to .env.local, then exits.
// Run: node oauth-listen.mjs   (run AFTER oauth-prep.mjs, then open the printed URL)
import http from 'http';
import fs from 'fs';

const session = JSON.parse(fs.readFileSync('.oauth-session.json', 'utf8'));
const PORT = new URL(session.redirect_uri).port || 3456;

console.log('Listening on port ' + PORT + ' — waiting for you to click Allow in your browser...');

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://localhost:${PORT}`);
  if (url.pathname !== '/callback') { res.end('ok'); return; }

  const code = url.searchParams.get('code');
  const returnedState = url.searchParams.get('state');
  const error = url.searchParams.get('error');

  if (error) {
    res.end('<h2>Etsy returned an error: ' + error + '. Close this tab and check the terminal.</h2>');
    console.error('ETSY_ERROR:', error, url.searchParams.get('error_description'));
    return;
  }
  if (!code || returnedState !== session.state) {
    res.end('<h2>State mismatch or missing code. Close this tab and check the terminal.</h2>');
    console.error('STATE_MISMATCH_OR_NO_CODE');
    return;
  }

  res.end('<h2>Authorized! You can close this tab and go back to Claude Code.</h2>');

  try {
    const tokenRes = await fetch('https://api.etsy.com/v3/public/oauth/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        grant_type: 'authorization_code',
        client_id: session.client_id,
        redirect_uri: session.redirect_uri,
        code,
        code_verifier: session.verifier,
      }),
    });
    const data = await tokenRes.json();
    if (!tokenRes.ok) {
      console.error('TOKEN_EXCHANGE_FAILED:', JSON.stringify(data));
      process.exitCode = 1;
      server.close();
      return;
    }
    const lines = fs.readFileSync('.env.local', 'utf8')
      .split('\n')
      .filter(l => !l.startsWith('ETSY_ACCESS_TOKEN') && !l.startsWith('ETSY_REFRESH_TOKEN'));
    lines.push(`ETSY_ACCESS_TOKEN=${data.access_token}`);
    lines.push(`ETSY_REFRESH_TOKEN=${data.refresh_token}`);
    fs.writeFileSync('.env.local', lines.join('\n') + '\n');
    fs.unlinkSync('.oauth-session.json');
    console.log('OAUTH_SUCCESS: tokens saved to .env.local');
    server.close();
  } catch (e) {
    console.error('OAUTH_EXCHANGE_ERROR:', e.message);
    process.exitCode = 1;
    server.close();
  }
});

server.listen(PORT);
