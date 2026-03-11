<template>
  <div class="response-viewer" v-if="response">
    <div class="response-header">
      <span class="status" :class="statusClass">{{ response.status }} {{ response.statusText }}</span>
      <span class="duration">{{ response.duration }}ms</span>
    </div>
    <pre class="response-body"><code>{{ formatted }}</code></pre>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ApiResponse } from '@/types/api'

const props = defineProps<{ response: ApiResponse }>()

const formatted = computed(() => {
  if (typeof props.response.data === 'string') return props.response.data
  return JSON.stringify(props.response.data, null, 2)
})

const statusClass = computed(() => {
  const s = props.response.status
  if (s >= 200 && s < 300) return 'success'
  if (s >= 400 && s < 500) return 'client-error'
  if (s >= 500) return 'server-error'
  return 'unknown'
})
</script>

<style scoped>
.response-viewer {
  margin-top: 12px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
}
.response-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
  font-size: 13px;
}
.status { font-weight: 600; }
.status.success { color: #166534; }
.status.client-error { color: #92400e; }
.status.server-error { color: #991b1b; }
.status.unknown { color: #6b7280; }
.duration { color: #6b7280; }
.response-body {
  padding: 12px;
  margin: 0;
  background: #1e293b;
  color: #e2e8f0;
  font-size: 13px;
  overflow-x: auto;
  max-height: 400px;
  overflow-y: auto;
}
</style>
