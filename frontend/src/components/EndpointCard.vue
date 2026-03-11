<template>
  <div class="endpoint-card" :class="{ expanded }">
    <div class="card-header" @click="expanded = !expanded">
      <div class="header-left">
        <StatusBadge :method="endpoint.method" />
        <code class="path">{{ endpoint.path }}</code>
        <span v-if="endpoint.auth" class="auth-icon" title="Requires API key">&#128274;</span>
      </div>
      <div class="header-right">
        <span class="summary">{{ endpoint.summary }}</span>
        <span class="chevron">{{ expanded ? '&#9650;' : '&#9660;' }}</span>
      </div>
    </div>

    <div v-if="expanded" class="card-body">
      <p class="description">{{ endpoint.description }}</p>

      <RequestBuilder
        :endpoint="endpoint"
        :values="paramValues"
        :body-text="rawBody"
        :loading="loading"
        @update:bodyText="rawBody = $event"
        @update:value="(name, val) => paramValues[name] = val"
        @send="send"
      />

      <div v-if="endpoint.exampleResponse" class="example">
        <h4>Example Response</h4>
        <pre><code>{{ formatJson(endpoint.exampleResponse) }}</code></pre>
      </div>

      <ResponseViewer v-if="response" :response="response" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import type { EndpointDef } from '@/types/api'
import { useApi } from '@/composables/useApi'
import StatusBadge from './StatusBadge.vue'
import RequestBuilder from './RequestBuilder.vue'
import ResponseViewer from './ResponseViewer.vue'

const props = defineProps<{ endpoint: EndpointDef }>()

const expanded = ref(false)
const paramValues = reactive<Record<string, string>>({})
const rawBody = ref('')
const { loading, response, sendRequest } = useApi()

watch(() => props.endpoint.id, () => {
  // Pre-fill body with example
  if (props.endpoint.exampleRequest) {
    rawBody.value = JSON.stringify(props.endpoint.exampleRequest, null, 2)
  }
}, { immediate: true })

function formatJson(val: unknown): string {
  if (typeof val === 'string') return val
  return JSON.stringify(val, null, 2)
}

function send() {
  let path = props.endpoint.path
  const queryParams: Record<string, string> = {}
  let body: Record<string, unknown> | undefined

  for (const param of props.endpoint.params) {
    const val = paramValues[param.name]
    if (param.in === 'path' && val) {
      path = path.replace(`{${param.name}}`, encodeURIComponent(val))
    } else if (param.in === 'query' && val) {
      queryParams[param.name] = val
    }
  }

  if (['POST', 'PUT'].includes(props.endpoint.method) && rawBody.value.trim()) {
    try {
      body = JSON.parse(rawBody.value)
    } catch {
      body = undefined
    }
  }

  sendRequest(props.endpoint.method, path, body, queryParams)
}
</script>

<style scoped>
.endpoint-card {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  margin-bottom: 8px;
  overflow: hidden;
  transition: box-shadow 0.15s;
}
.endpoint-card:hover {
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.endpoint-card.expanded {
  border-color: #93c5fd;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  cursor: pointer;
  background: #fafafa;
  gap: 12px;
}
.card-header:hover { background: #f3f4f6; }
.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.path {
  font-size: 13px;
  color: #374151;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.auth-icon { font-size: 12px; }
.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}
.summary {
  font-size: 13px;
  color: #6b7280;
}
.chevron { font-size: 10px; color: #9ca3af; }
.card-body {
  padding: 16px;
  border-top: 1px solid #e5e7eb;
}
.description {
  margin: 0 0 12px;
  font-size: 14px;
  line-height: 1.5;
  color: #4b5563;
}
.example { margin-top: 16px; }
.example h4 {
  margin: 0 0 6px;
  font-size: 13px;
  color: #6b7280;
}
.example pre {
  background: #f8fafc;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 10px;
  font-size: 12px;
  overflow-x: auto;
  margin: 0;
}
</style>
