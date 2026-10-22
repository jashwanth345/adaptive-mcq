export function localOrigin(value = 'http://127.0.0.1:8000'): string {
  const url = new URL(value);
  if (url.protocol !== 'http:' || !['localhost', '127.0.0.1', '[::1]'].includes(url.hostname)
    || url.username || url.password || url.pathname !== '/' || url.search || url.hash) {
    throw new Error('LOCAL_API_ORIGIN must be an HTTP loopback origin without credentials or a path.');
  }
  return url.origin;
}
