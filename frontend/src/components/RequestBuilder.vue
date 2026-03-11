<template>
  <div class="request-builder" v-if="endpoint.params.length > 0 || hasBody">
    <h4>Parameters</h4>
    <div class="params">
      <div v-for="param in endpoint.params" :key="param.name" class="param-row">
        <label>
          <span class="param-name">{{ param.name }}</span>
          <span class="param-meta">
            <span class="param-in">{{ param.in }}</span>
            <span v-if="param.required" class="required">required</span>
          </span>
        </label>
        <input
          v-if="param.type !== 'boolean'"
          :type="param.type === 'number' ? 'number' : 'text'"
          :placeholder="param.description"
          :value="values[param.name] || ''"
          @input="updateValue(param.name, ($event.target as HTMLInputElement).value)"
        />
        <select v-else :value="values[param.name] || ''" @change="updateValue(param.name, ($event.target as HTMLSelectElement).value)">
          <option value="">--</option>
          <option value="true">true</option>
          <option value="false">false</option>
        </select>
        <span class="param-desc">{{ param.description }}</span>
      </div>
    </div>

    <div v-if="hasBody" class="body-editor">
      <h4>Request Body (JSON)</h4>
      <textarea :value="bodyText" @input="$emit('update:bodyText', ($event.target as HTMLTextAreaElement).value)" rows="6" placeholder="{ }"></textarea>
    </div>
  </div>

  <div class="actions">
    <button class="send-btn" :class="endpoint.method.toLowerCase()" @click="$emit('send')" :disabled="loading">
      {{ loading ? 'Sending...' : `Send ${endpoint.method}` }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { EndpointDef } from '@/types/api'

const props = defineProps<{
  endpoint: EndpointDef
  values: Record<string, string>
  bodyText: string
  loading: boolean
}>()

const emit = defineEmits<{
  send: []
  'update:bodyText': [value: string]
  'update:value': [name: string, value: string]
}>()

const hasBody = computed(() =>
  ['POST', 'PUT'].includes(props.endpoint.method) && props.endpoint.params.some(p => p.in === 'body')
)

function updateValue(name: string, value: string) {
  emit('update:value', name, value)
}
</script>

<style scoped>
.request-builder { margin-top: 16px; }
h4 { margin: 0 0 8px; font-size: 14px; color: #374151; }
.params { display: flex; flex-direction: column; gap: 8px; }
.param-row {
  display: grid;
  grid-template-columns: 160px 1fr;
  grid-template-rows: auto auto;
  gap: 4px 12px;
  align-items: center;
}
.param-row label {
  display: flex;
  align-items: center;
  gap: 6px;
}
.param-name { font-weight: 600; font-size: 13px; font-family: monospace; }
.param-meta { display: flex; gap: 4px; }
.param-in {
  font-size: 10px;
  padding: 1px 4px;
  background: #f3f4f6;
  border-radius: 3px;
  color: #6b7280;
}
.required { font-size: 10px; color: #dc2626; }
.param-desc {
  grid-column: 1 / -1;
  font-size: 12px;
  color: #9ca3af;
}
input, select {
  padding: 6px 8px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 13px;
}
.body-editor { margin-top: 12px; }
textarea {
  width: 100%;
  padding: 8px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-family: monospace;
  font-size: 13px;
  resize: vertical;
  box-sizing: border-box;
}
.actions { margin-top: 12px; }
.send-btn {
  padding: 8px 20px;
  border: none;
  border-radius: 6px;
  font-weight: 600;
  font-size: 14px;
  cursor: pointer;
  color: white;
}
.send-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.send-btn.get { background: #16a34a; }
.send-btn.post { background: #2563eb; }
.send-btn.put { background: #d97706; }
.send-btn.delete { background: #dc2626; }
</style>
