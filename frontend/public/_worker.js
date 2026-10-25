const BACKEND_ORIGIN = 'https://api-life.kaenthong-mansion.com'

export default {
  async fetch(request, env) {
    const url = new URL(request.url)

    // 1. Reverse proxy /api/* and /ws/* (Interactive SSH WebSocket) to Backend Cloudflare Tunnel
    if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/ws/')) {
      const targetUrl = `${BACKEND_ORIGIN}${url.pathname}${url.search}`
      const headers = new Headers(request.headers)
      headers.delete('Host')
      headers.set('X-Forwarded-Host', url.host)
      headers.set('X-Forwarded-Proto', url.protocol.replace(':', ''))

      const proxyRequest = new Request(targetUrl, {
        method: request.method,
        headers,
        body:
          request.method !== 'GET' && request.method !== 'HEAD'
            ? request.body
            : null,
        redirect: 'manual',
      })

      return fetch(proxyRequest)
    }

    // 2. Serve static files from Vite dist; fallback to /index.html for SPA routes
    const response = await env.ASSETS.fetch(request)
    if (response.status === 404 && !url.pathname.includes('.')) {
      return env.ASSETS.fetch(new Request(new URL('/index.html', request.url), request))
    }
    return response
  },
}
