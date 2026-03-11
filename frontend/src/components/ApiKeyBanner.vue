<template>
  <div class="banner" v-if="!store.isConfigured">
    <span>API key not set.</span>
    <router-link to="/settings">Configure</router-link>
  </div>
</template>

<script setup lang="ts">
import { useApiStore } from '@/stores/api'
const store = useApiStore()
</script>

<style scoped>
.banner {
  background: #fef3c7;
  color: #92400e;
  padding: 8px 16px;
  text-align: center;
  font-size: 14px;
  border-bottom: 1px solid #fcd34d;
}
.banner a {
  color: #1e40af;
  margin-left: 8px;
  font-weight: 600;
}
</style>
