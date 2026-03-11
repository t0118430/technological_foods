<template>
  <div class="home">
    <h2>AgriTech Hydroponics API Portal</h2>
    <p class="subtitle">Explore and test all {{ totalEndpoints }} API endpoints across {{ categories.length }} categories.</p>

    <div class="health-section">
      <h3>System Health</h3>
      <div v-if="healthData" class="health-card success">
        <span class="health-status">&#9679; {{ (healthData as any).status || 'connected' }}</span>
        <span class="health-detail">Base URL: {{ store.baseUrl }}</span>
      </div>
      <div v-else-if="healthError" class="health-card error">
        <span class="health-status">&#9679; unreachable</span>
        <span class="health-detail">{{ healthError }}</span>
      </div>
      <button class="check-btn" @click="checkHealth" :disabled="healthLoading">
        {{ healthLoading ? 'Checking...' : 'Check Health' }}
      </button>
    </div>

    <div class="categories-grid">
      <router-link
        v-for="cat in categories"
        :key="cat.id"
        :to="`/category/${cat.id}`"
        class="category-card"
      >
        <div class="cat-icon" v-html="cat.icon"></div>
        <div class="cat-info">
          <h4>{{ cat.name }}</h4>
          <p>{{ cat.description }}</p>
          <span class="cat-count">{{ countEndpoints(cat.id) }} endpoints</span>
        </div>
      </router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useApiStore } from '@/stores/api'
import { categories, endpoints } from '@/data/endpoints'

const store = useApiStore()
const totalEndpoints = endpoints.length

const healthData = ref<unknown>(null)
const healthError = ref<string | null>(null)
const healthLoading = ref(false)

function countEndpoints(catId: string): number {
  return endpoints.filter(e => e.category === catId).length
}

async function checkHealth() {
  healthLoading.value = true
  healthData.value = null
  healthError.value = null
  try {
    const res = await fetch(`${store.baseUrl}/api/health`)
    healthData.value = await res.json()
  } catch (e) {
    healthError.value = e instanceof Error ? e.message : 'Connection failed'
  } finally {
    healthLoading.value = false
  }
}

onMounted(checkHealth)
</script>

<style scoped>
.home { max-width: 900px; }
h2 { margin: 0 0 4px; font-size: 24px; color: #111827; }
.subtitle { margin: 0 0 24px; color: #6b7280; font-size: 15px; }

.health-section {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 16px;
  margin-bottom: 28px;
}
.health-section h3 { margin: 0 0 10px; font-size: 15px; }
.health-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 14px;
  margin-bottom: 10px;
}
.health-card.success { background: #dcfce7; color: #166534; }
.health-card.error { background: #fde2e2; color: #991b1b; }
.health-status { font-weight: 600; }
.health-detail { color: inherit; opacity: 0.7; }
.check-btn {
  padding: 6px 14px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: white;
  cursor: pointer;
  font-size: 13px;
}
.check-btn:hover { background: #f3f4f6; }
.check-btn:disabled { opacity: 0.5; }

.categories-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 12px;
}
.category-card {
  display: flex;
  gap: 12px;
  padding: 14px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  text-decoration: none;
  color: inherit;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.category-card:hover {
  border-color: #93c5fd;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.cat-icon { font-size: 24px; padding-top: 2px; }
.cat-info h4 { margin: 0 0 2px; font-size: 14px; color: #111827; }
.cat-info p { margin: 0 0 4px; font-size: 12px; color: #6b7280; line-height: 1.4; }
.cat-count { font-size: 11px; color: #9ca3af; }
</style>
