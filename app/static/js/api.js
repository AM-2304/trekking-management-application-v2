/*
 * Small wrapper around fetch(). Same-origin, so the session cookie goes along
 * automatically and there is no token to attach. Throws an Error carrying the
 * message the API sent.
 */
const api = {
  async request(path, options = {}) {
    const response = await fetch(path, {
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      ...options,
    });

    const text = await response.text();
    const data = text ? JSON.parse(text) : {};

    if (!response.ok) {
      const error = new Error(data.error || 'Something went wrong');
      error.status = response.status;
      throw error;
    }
    return data;
  },

  get(path) {
    return this.request(path);
  },
  post(path, body) {
    return this.request(path, { method: 'POST', body: JSON.stringify(body || {}) });
  },
  put(path, body) {
    return this.request(path, { method: 'PUT', body: JSON.stringify(body || {}) });
  },
  del(path) {
    return this.request(path, { method: 'DELETE' });
  },
};
