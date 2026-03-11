<template>
  <div class="category-view" v-if="category">
    <div class="category-header">
      <span class="cat-icon" v-html="category.icon"></span>
      <div>
        <h2>{{ category.name }}</h2>
        <p>{{ category.description }}</p>
      </div>
    </div>

    <div v-if="filteredEndpoints.length === 0" class="empty">
      No endpoints match your search.
    </div>

    <EndpointCard
      v-for="ep in filteredEndpoints"
      :key="ep.id"
      :endpoint="ep"
    />
  </div>
  <div v-else class="not-found">
    <h2>Category not found</h2>
    <router-link to="/">Back to overview</router-link>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useApiStore } from '@/stores/api'
import { categories, endpoints } from '@/data/endpoints'
import EndpointCard from '@/components/EndpointCard.vue'

const route = useRoute()
const store = useApiStore()

const category = computed(() =>
  categories.find(c => c.id === route.params.id)
)

const filteredEndpoints = computed(() => {
  const catEndpoints = endpoints.filter(e => e.category === route.params.id)
  const q = store.searchQuery.toLowerCase().trim()
  if (!q) return catEndpoints
  return catEndpoints.filter(e =>
    e.summary.toLowerCase().includes(q) ||
    e.path.toLowerCase().includes(q) ||
    e.description.toLowerCase().includes(q)
  )
})
</script>

<style scoped>
.category-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}
.cat-icon { font-size: 28px; }
.category-header h2 { margin: 0; font-size: 22px; color: #111827; }
.category-header p { margin: 2px 0 0; color: #6b7280; font-size: 14px; }
.empty {
  padding: 40px;
  text-align: center;
  color: #9ca3af;
  font-size: 14px;
}
.not-found { text-align: center; padding: 60px 20px; }
.not-found a { color: #2563eb; }
</style>
