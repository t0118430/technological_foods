import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useApiStore = defineStore('api', () => {
  const baseUrl = ref(localStorage.getItem('agritech_base_url') || 'http://localhost:3001')
  const apiKey = ref(localStorage.getItem('agritech_api_key') || '')
  const searchQuery = ref('')

  const isConfigured = computed(() => apiKey.value.length > 0)

  function setBaseUrl(url: string) {
    baseUrl.value = url.replace(/\/+$/, '')
    localStorage.setItem('agritech_base_url', baseUrl.value)
  }

  function setApiKey(key: string) {
    apiKey.value = key
    localStorage.setItem('agritech_api_key', key)
  }

  function setSearch(query: string) {
    searchQuery.value = query
  }

  return { baseUrl, apiKey, searchQuery, isConfigured, setBaseUrl, setApiKey, setSearch }
})
