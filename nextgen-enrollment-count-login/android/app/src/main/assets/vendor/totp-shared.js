// Pure JS SHA1 + HMAC-SHA1 + TOTP (RFC 6238), no dependencies, no network.
// Verified against Node's built-in crypto module before use.
(function(global){
  function rotl(n, s) { return ((n << s) | (n >>> (32 - s))) >>> 0; }

  function sha1(bytes) {
    const msgLen = bytes.length;
    const withOne = bytes.concat([0x80]);
    while (withOne.length % 64 !== 56) withOne.push(0);
    const bitLen = msgLen * 8;
    for (let i = 7; i >= 0; i--) withOne.push((bitLen / Math.pow(2, i * 8)) & 0xff);

    let h0 = 0x67452301, h1 = 0xEFCDAB89, h2 = 0x98BADCFE, h3 = 0x10325476, h4 = 0xC3D2E1F0;

    for (let chunkStart = 0; chunkStart < withOne.length; chunkStart += 64) {
      const w = new Array(80);
      for (let i = 0; i < 16; i++) {
        const o = chunkStart + i * 4;
        w[i] = ((withOne[o] << 24) | (withOne[o+1] << 16) | (withOne[o+2] << 8) | withOne[o+3]) >>> 0;
      }
      for (let i = 16; i < 80; i++) {
        w[i] = rotl(w[i-3] ^ w[i-8] ^ w[i-14] ^ w[i-16], 1);
      }
      let a = h0, b = h1, c = h2, d = h3, e = h4;
      for (let i = 0; i < 80; i++) {
        let f, k;
        if (i < 20) { f = (b & c) | ((~b) & d); k = 0x5A827999; }
        else if (i < 40) { f = b ^ c ^ d; k = 0x6ED9EBA1; }
        else if (i < 60) { f = (b & c) | (b & d) | (c & d); k = 0x8F1BBCDC; }
        else { f = b ^ c ^ d; k = 0xCA62C1D6; }
        const temp = (rotl(a, 5) + f + e + k + w[i]) >>> 0;
        e = d; d = c; c = rotl(b, 30); b = a; a = temp;
      }
      h0 = (h0 + a) >>> 0; h1 = (h1 + b) >>> 0; h2 = (h2 + c) >>> 0; h3 = (h3 + d) >>> 0; h4 = (h4 + e) >>> 0;
    }
    return [h0, h1, h2, h3, h4].reduce((arr, h) => {
      arr.push((h >>> 24) & 0xff, (h >>> 16) & 0xff, (h >>> 8) & 0xff, h & 0xff);
      return arr;
    }, []);
  }

  function hmacSha1(keyBytes, msgBytes) {
    const blockSize = 64;
    if (keyBytes.length > blockSize) keyBytes = sha1(keyBytes);
    const key = keyBytes.slice();
    while (key.length < blockSize) key.push(0);
    const oKeyPad = key.map(b => b ^ 0x5c);
    const iKeyPad = key.map(b => b ^ 0x36);
    const inner = sha1(iKeyPad.concat(msgBytes));
    return sha1(oKeyPad.concat(inner));
  }

  function strToBytes(str) {
    return Array.from(str).map(c => c.charCodeAt(0));
  }

  function counterToBytes(counter) {
    const bytes = new Array(8).fill(0);
    for (let i = 7; i >= 0; i--) {
      bytes[i] = counter & 0xff;
      counter = Math.floor(counter / 256);
    }
    return bytes;
  }

  function totp(secretStr, timeStepSec, digits, unixSeconds) {
    const counter = Math.floor(unixSeconds / timeStepSec);
    const hmac = hmacSha1(strToBytes(secretStr), counterToBytes(counter));
    const offset = hmac[hmac.length - 1] & 0xf;
    const binCode = ((hmac[offset] & 0x7f) << 24) | ((hmac[offset+1] & 0xff) << 16) | ((hmac[offset+2] & 0xff) << 8) | (hmac[offset+3] & 0xff);
    const code = binCode % Math.pow(10, digits);
    return String(code).padStart(digits, '0');
  }

  global.NextGenTOTP = { totp, sha1, hmacSha1 };
})(typeof window !== 'undefined' ? window : this);
