'use strict';

const express = require('express');
const qrcode = require('qrcode');
const fs = require('fs');
const path = require('path');

const PORT = 3001;
const AUTH_STORE = path.join(__dirname, 'auth_store');

let sock = null;
let currentQR = null;
let isConnected = false;
let connectedPhone = '';
let isLoggedOut = false;

// ── AI message-processing state ───────────────────────────────────────────────
const processedMsgIds = new Set();   // dedup — keep last 50 IDs
let lastBotReplyTime  = 0;           // timestamp of our last sent reply
let lastProcessedTime = 0;           // timestamp of last Gemini call (rate limit)
let consecutiveErrors = 0;           // suppress error replies after 2 in a row

const BOT_REPLY_PREFIXES = ['✅', '❌', '⚠️', '📦', '🚛', '📊', '━', '🤖'];
const TRIP_KEYWORDS = [
  'ton', 'tonne', 'mt', 'kg',
  'steel', 'iron', 'cement', 'coal', 'sand', 'gravel', 'cotton', 'grain',
  'transport', 'deliver', 'pickup', 'load', 'cargo', 'goods', 'material',
  'from', 'to', 'se', 'tak', 'bhejo', 'trip', 'gaadi', 'truck',
];

async function connectToWhatsApp() {
  const baileys = require('baileys');
  const makeWASocket = baileys.default || baileys.makeWASocket || baileys;
  const { useMultiFileAuthState, DisconnectReason } = baileys;

  const { state, saveCreds } = await useMultiFileAuthState(AUTH_STORE);

  sock = makeWASocket({
    auth: state,
    printQRInTerminal: false,
    browser: ['DispatchIQ', 'Chrome', '1.0.0'],
  });

  sock.ev.on('creds.update', saveCreds);

  sock.ev.on('connection.update', async (update) => {
    const { connection, lastDisconnect, qr } = update;

    if (qr) {
      try {
        currentQR = await qrcode.toDataURL(qr);
        isConnected = false;
        console.log('[WA] QR code ready — scan with WhatsApp');
      } catch (err) {
        console.error('[WA] QR generation error:', err.message);
      }
    }

    if (connection === 'open') {
      isConnected = true;
      currentQR = null;
      isLoggedOut = false;
      connectedPhone = sock.user?.id?.split(':')[0] || '';
      console.log(`[WA] Connected as ${connectedPhone}`);
    }

    if (connection === 'close') {
      const statusCode = lastDisconnect?.error?.output?.statusCode;
      const { Boom } = require('@hapi/boom');
      const shouldLogout =
        lastDisconnect?.error instanceof Boom &&
        statusCode === DisconnectReason.loggedOut;

      isConnected = false;
      connectedPhone = '';

      if (shouldLogout) {
        console.log('[WA] Logged out — deleting auth store');
        isLoggedOut = true;
        try { fs.rmSync(AUTH_STORE, { recursive: true, force: true }); } catch (_) {}
      } else if (!isLoggedOut) {
        console.log('[WA] Connection closed — reconnecting in 3s...');
        setTimeout(connectToWhatsApp, 3000);
      }
    }
  });

  sock.ev.on('messages.upsert', async (m) => {
    const msg = m.messages[0];
    if (!msg.message) return;

    // Only process direct messages, not groups or newsletters
    if (msg.key.remoteJid.includes('@g.us') || msg.key.remoteJid.includes('@newsletter')) return;

    const msgId  = msg.key.id;
    const text   = (msg.message.conversation ||
                    msg.message.extendedTextMessage?.text || '').trim();
    const sender = msg.key.remoteJid.replace('@s.whatsapp.net', '');

    console.log('══════════════════════════════════');
    console.log('📩 MESSAGE RECEIVED');
    console.log('From:', sender);
    console.log('Text:', text);
    console.log('fromMe:', msg.key.fromMe);
    console.log('══════════════════════════════════');

    if (!text) return;

    // BUG 1 — skip own bot replies (prefix check stops the infinite loop)
    if (msg.key.fromMe && BOT_REPLY_PREFIXES.some(p => text.startsWith(p))) {
      console.log('⏭️ Message skipped — reason: own_reply (bot prefix)');
      return;
    }

    // BUG 1 — skip if arrived within 2 s of our last sent reply
    if (Date.now() - lastBotReplyTime < 2000) {
      console.log('⏭️ Message skipped — reason: own_reply (timing window)');
      return;
    }

    // BUG 1 — dedup by message ID
    if (processedMsgIds.has(msgId)) {
      console.log('⏭️ Message skipped — reason: duplicate_id');
      return;
    }

    // BUG 3 — rate limit: 1 Gemini call per 10 s
    if (Date.now() - lastProcessedTime < 10000) {
      console.log('⏭️ Message skipped — reason: cooldown');
      return;
    }

    // Only forward messages that look like trip commands
    const lowerText = text.toLowerCase();
    if (!TRIP_KEYWORDS.some(kw => lowerText.includes(kw))) {
      console.log('⏭️ Message skipped — reason: no trip keywords');
      return;
    }

    // Mark ID as seen (cap set at 50 entries)
    processedMsgIds.add(msgId);
    if (processedMsgIds.size > 50) {
      processedMsgIds.delete(processedMsgIds.values().next().value);
    }

    try {
      // fromMe === true → the connected account sent it, always the owner.
      // For incoming messages (fromMe=false), compare against stored owner phone.
      let confirmed = msg.key.fromMe;
      if (!confirmed) {
        const configRes = await fetch('http://localhost:5000/api/settings/owner-phone');
        const config    = await configRes.json();
        const ownerPhone  = (config.owner_phone || '').replace(/[^0-9]/g, '');
        const senderClean = sender.replace(/[^0-9]/g, '');
        confirmed = ownerPhone && senderClean === ownerPhone;
      }

      if (!confirmed) {
        console.log(`[WA] Ignoring message from non-owner: ${sender}`);
        return;
      }

      lastProcessedTime = Date.now();
      console.log('🚀 Sending to Flask:', text);

      const res    = await fetch('http://localhost:5000/api/ai/parse-trip', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, sender }),
      });
      const result = await res.json();
      console.log('📬 Flask replied:', JSON.stringify(result));

      if (result.reply) {
        // BUG 4 — suppress error replies after 2 consecutive failures
        if (!result.success && consecutiveErrors >= 2) {
          console.log('⏭️ Message skipped — reason: repeated_error (suppressing reply)');
          consecutiveErrors++;
          return;
        }

        lastBotReplyTime = Date.now();
        await sock.sendMessage(msg.key.remoteJid, { text: result.reply });
        console.log('[WA] AI reply sent');

        if (result.success) {
          consecutiveErrors = 0;   // reset on successful trip creation
        } else {
          consecutiveErrors++;
        }
      }
    } catch (err) {
      console.log('❌ Error:', err.message);
    }
  });
}

// ── Express ──────────────────────────────────────────────────────────────────

const app = express();
app.use(express.json());
app.use(express.urlencoded({ extended: false }));

function page(body, autoRefresh = false) {
  const refresh = autoRefresh ? '<meta http-equiv="refresh" content="5">' : '';
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  ${refresh}
  <title>WhatsApp Sender — DispatchIQ</title>
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    body{background:#030712;color:#f9fafb;font-family:system-ui,sans-serif;
         min-height:100vh;display:flex;flex-direction:column;align-items:center;
         justify-content:center;padding:2rem}
    h1{font-size:1.5rem;font-weight:700;margin-bottom:.5rem;color:#f9fafb}
    h2{font-size:1rem;color:#9ca3af;margin-bottom:2rem;font-weight:400}
    .card{background:#111827;border:1px solid #1f2937;border-radius:.75rem;
          padding:2rem;max-width:420px;width:100%;text-align:center}
    img{border-radius:.5rem;margin:1rem auto;display:block;max-width:280px}
    .hint{color:#6b7280;font-size:.85rem;margin-top:1rem;line-height:1.5}
    .connected{color:#4ade80;font-size:1.25rem;margin:1rem 0}
    .phone{color:#9ca3af;font-size:.9rem;margin-bottom:1.5rem}
    button{background:#dc2626;color:#fff;border:none;padding:.6rem 1.5rem;
           border-radius:.375rem;cursor:pointer;font-size:.9rem;font-weight:500}
    button:hover{background:#b91c1c}
    .dot-wait{color:#fbbf24;font-size:1rem;margin-bottom:1rem}
  </style>
</head>
<body>
  <div class="card">
    <h1>🚚 DispatchIQ</h1>
    <h2>WhatsApp Sender Service</h2>
    ${body}
  </div>
</body>
</html>`;
}

app.get('/', (req, res) => {
  if (isConnected) {
    res.send(page(`
      <div class="connected">✅ WhatsApp Connected</div>
      <div class="phone">📱 ${connectedPhone}</div>
      <form method="POST" action="/disconnect">
        <button type="submit">Disconnect</button>
      </form>
    `));
  } else if (currentQR) {
    res.send(page(`
      <div class="dot-wait">⏳ Waiting for QR scan...</div>
      <img src="${currentQR}" alt="WhatsApp QR Code">
      <div class="hint">
        Open WhatsApp → Linked Devices → Link a Device<br>
        Scan the QR code above.<br>
        This page refreshes every 5 seconds.
      </div>
    `, true));
  } else {
    res.send(page(`
      <div class="dot-wait">🔄 Connecting to WhatsApp...</div>
      <div class="hint">Please wait while the connection is established.</div>
    `, true));
  }
});

app.get('/status', (req, res) => {
  res.json({ connected: isConnected, phone: connectedPhone });
});

app.post('/send', async (req, res) => {
  if (!isConnected || !sock) {
    return res.status(503).json({ error: 'WhatsApp not connected' });
  }
  const { phone, message } = req.body || {};
  if (!phone || !message) {
    return res.status(400).json({ error: 'phone and message are required' });
  }
  try {
    const jid = phone.replace(/[^0-9]/g, '') + '@s.whatsapp.net';
    await sock.sendMessage(jid, { text: String(message) });
    console.log(`[WA] Message sent to ${phone}`);
    res.json({ success: true });
  } catch (err) {
    console.error('[WA] Send error:', err.message);
    res.status(500).json({ error: err.message });
  }
});

app.post('/disconnect', async (req, res) => {
  isLoggedOut = true;
  try {
    if (sock) await sock.logout();
  } catch (_) {}
  try { fs.rmSync(AUTH_STORE, { recursive: true, force: true }); } catch (_) {}
  isConnected = false;
  currentQR = null;
  connectedPhone = '';
  isLoggedOut = false;
  setTimeout(connectToWhatsApp, 500);
  res.redirect('/');
});

// ── Start ─────────────────────────────────────────────────────────────────────

app.listen(PORT, () => {
  console.log(`[WA] Server running at http://localhost:${PORT}`);
  connectToWhatsApp().catch(err => console.error('[WA] Connect error:', err.message));
});
