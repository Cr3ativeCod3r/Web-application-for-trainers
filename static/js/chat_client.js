/**
 * Talks to the chat microservice on behalf of the logged-in user.
 *
 * Tokens are short-lived and fetched from the main app (session + CSRF) when
 * needed, so no long-lived credential is embedded in the page. WebSockets are
 * opened with a one-time ticket instead of a token in the URL.
 */
class ChatClient {
  constructor({ apiBase, wsBase, tokenUrl, csrfToken }) {
    this.apiBase = apiBase;
    this.wsBase = wsBase;
    this.tokenUrl = tokenUrl;
    this.csrfToken = csrfToken;
    this.token = null;
    this.tokenExpiresAt = 0;
    this.pendingToken = null;
  }

  async getToken(forceRefresh = false) {
    // Renew 30 s early so a request never leaves with a token about to expire.
    if (!forceRefresh && this.token && Date.now() < this.tokenExpiresAt - 30_000) {
      return this.token;
    }
    // Concurrent callers share one refresh request.
    if (!this.pendingToken) {
      this.pendingToken = fetch(this.tokenUrl, {
        method: 'POST',
        headers: { 'X-CSRFToken': this.csrfToken },
        credentials: 'same-origin',
      })
        .then(res => {
          if (!res.ok) throw new Error(`Token request failed (${res.status})`);
          return res.json();
        })
        .then(data => {
          this.token = data.token;
          this.tokenExpiresAt = Date.now() + data.expires_in * 1000;
          return this.token;
        })
        .finally(() => { this.pendingToken = null; });
    }
    return this.pendingToken;
  }

  async request(path, options = {}) {
    const send = async (token) => fetch(this.apiBase + path, {
      ...options,
      headers: { ...(options.headers || {}), 'Authorization': 'Bearer ' + token },
    });
    let res = await send(await this.getToken());
    if (res.status === 401) {
      // Clock skew or a revoked token: retry once with a fresh one.
      res = await send(await this.getToken(true));
    }
    return res;
  }

  async openSocket(roomId) {
    const res = await this.request('/ws-tickets', { method: 'POST' });
    if (!res.ok) throw new Error(`Ticket request failed (${res.status})`);
    const { ticket } = await res.json();
    return new WebSocket(`${this.wsBase}/ws/chat/${encodeURIComponent(roomId)}?ticket=${encodeURIComponent(ticket)}`);
  }
}
