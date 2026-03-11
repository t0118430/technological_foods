<template>
  <div class="settings">
    <h2>Settings</h2>
    <p class="subtitle">Configure API connection settings. Values are stored in your browser.</p>

    <div class="settings-card">
      <div class="field">
        <label for="baseUrl">Base URL</label>
        <input
          id="baseUrl"
          type="text"
          :value="store.baseUrl"
          @input="store.setBaseUrl(($event.target as HTMLInputElement).value)"
          placeholder="http://localhost:3001"
        />
        <span class="hint">The backend server address (no trailing slash)</span>
      </div>

      <div class="field">
        <label for="apiKey">API Key</label>
        <div class="key-input">
          <input
            id="apiKey"
            :type="showKey ? 'text' : 'password'"
            :value="store.apiKey"
            @input="store.setApiKey(($event.target as HTMLInputElement).value)"
            placeholder="Enter your API key"
          />
          <button class="toggle-btn" @click="showKey = !showKey">
            {{ showKey ? 'Hide' : 'Show' }}
          </button>
        </div>
        <span class="hint">Sent as X-API-Key header. Leave empty if auth is disabled on the backend.</span>
      </div>
    </div>

    <div class="test-section">
      <h3>Test Connection</h3>
      <button @click="testConnection" :disabled="testing" class="test-btn">
        {{ testing ? 'Testing...' : 'Test Connection' }}
      </button>
      <div v-if="testResult" class="test-result" :class="testResult.ok ? 'success' : 'error'">
        {{ testResult.message }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useApiStore } from '@/stores/api'

const store = useApiStore()
const showKey = ref(false)
const testing = ref(false)
const testResult = ref<{ ok: boolean; message: string } | null>(null)

async function testConnection() {
  testing.value = true
  testResult.value = null
  try {
    const res = await fetch(`${store.baseUrl}/api/health`, {
      headers: store.apiKey ? { 'X-API-Key': store.apiKey } : {},
    })
    if (res.ok) {
      const data = await res.json()
      testResult.value = { ok: true, message: `Connected! Status: ${data.status || 'ok'}` }
    } else {
      testResult.value = { ok: false, message: `HTTP ${res.status}: ${res.statusText}` }
    }
  } catch (e) {
    testResult.value = { ok: false, message: e instanceof Error ? e.message : 'Connection failed' }
  } finally {
    testing.value = false
  }
}
</script>

<style scoped>
.settings { max-width: 600px; }
h2 { margin: 0 0 4px; font-size: 22px; }
.subtitle { margin: 0 0 20px; color: #6b7280; font-size: 14px; }

.settings-card {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.field label {
  display: block;
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 4px;
}
.field input {
  width: 100%;
  padding: 8px 10px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  box-sizing: border-box;
}
.key-input { display: flex; gap: 8px; }
.key-input input { flex: 1; }
.toggle-btn {
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: white;
  cursor: pointer;
  font-size: 13px;
}
.hint { font-size: 12px; color: #9ca3af; margin-top: 2px; display: block; }

.test-section { margin-top: 24px; }
.test-section h3 { margin: 0 0 10px; font-size: 15px; }
.test-btn {
  padding: 8px 16px;
  background: #2563eb;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
}
.test-btn:disabled { opacity: 0.5; }
.test-result {
  margin-top: 10px;
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 14px;
}
.test-result.success { background: #dcfce7; color: #166534; }
.test-result.error { background: #fde2e2; color: #991b1b; }
</style>
