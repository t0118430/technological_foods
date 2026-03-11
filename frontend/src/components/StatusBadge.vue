<template>
  <span class="badge" :class="method.toLowerCase()">{{ method }}</span>
</template>

<script setup lang="ts">
import type { HttpMethod } from '@/types/api'
defineProps<{ method: HttpMethod }>()
</script>

<style scoped>
.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 700;
  font-family: monospace;
  min-width: 56px;
  text-align: center;
}
.get { background: #dcfce7; color: #166534; }
.post { background: #dbeafe; color: #1e40af; }
.put { background: #fef3c7; color: #92400e; }
.delete { background: #fde2e2; color: #991b1b; }
</style>
