import { ref } from 'vue'
import { useApiStore } from '@/stores/api'
import type { ApiResponse, HttpMethod } from '@/types/api'

export function useApi() {
  const loading = ref(false)
  const response = ref<ApiResponse | null>(null)
  const error = ref<string | null>(null)

  async function sendRequest(
    method: HttpMethod,
    path: string,
    body?: Record<string, unknown>,
    queryParams?: Record<string, string>
  ): Promise<ApiResponse> {
    const store = useApiStore()
    loading.value = true
    error.value = null
    response.value = null

    let url = `${store.baseUrl}${path}`

    if (queryParams) {
      const params = new URLSearchParams()
      for (const [k, v] of Object.entries(queryParams)) {
        if (v !== '' && v !== undefined) params.append(k, v)
      }
      const qs = params.toString()
      if (qs) url += `?${qs}`
    }

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    }
    if (store.apiKey) {
      headers['X-API-Key'] = store.apiKey
    }

    const start = performance.now()

    try {
      const res = await fetch(url, {
        method,
        headers,
        body: method !== 'GET' && body ? JSON.stringify(body) : undefined,
      })

      const duration = Math.round(performance.now() - start)
      let data: unknown
      const contentType = res.headers.get('content-type') || ''
      if (contentType.includes('json')) {
        data = await res.json()
      } else {
        data = await res.text()
      }

      response.value = { status: res.status, statusText: res.statusText, data, duration }
      return response.value
    } catch (err) {
      const duration = Math.round(performance.now() - start)
      error.value = err instanceof Error ? err.message : 'Request failed'
      response.value = { status: 0, statusText: 'Network Error', data: error.value, duration }
      return response.value
    } finally {
      loading.value = false
    }
  }

  return { loading, response, error, sendRequest }
}
