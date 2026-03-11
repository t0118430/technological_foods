<template>
  <aside class="sidebar">
    <div class="logo">
      <h1>AgriTech API</h1>
    </div>

    <div class="search-box">
      <input
        type="text"
        placeholder="Search endpoints..."
        :value="store.searchQuery"
        @input="store.setSearch(($event.target as HTMLInputElement).value)"
      />
    </div>

    <nav>
      <router-link to="/" class="nav-item" :class="{ active: route.name === 'home' }">
        <span class="nav-icon">&#127968;</span>
        <span>Overview</span>
      </router-link>

      <div class="nav-section">Categories</div>

      <router-link
        v-for="cat in categories"
        :key="cat.id"
        :to="`/category/${cat.id}`"
        class="nav-item"
        :class="{ active: route.params.id === cat.id }"
      >
        <span class="nav-icon" v-html="cat.icon"></span>
        <span>{{ cat.name }}</span>
        <span class="count">{{ endpointCount(cat.id) }}</span>
      </router-link>

      <div class="nav-section">Config</div>

      <router-link to="/settings" class="nav-item" :class="{ active: route.name === 'settings' }">
        <span class="nav-icon">&#9881;</span>
        <span>Settings</span>
      </router-link>
    </nav>
  </aside>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
import { useApiStore } from '@/stores/api'
import { categories, endpoints } from '@/data/endpoints'

const route = useRoute()
const store = useApiStore()

function endpointCount(categoryId: string): number {
  return endpoints.filter(e => e.category === categoryId).length
}
</script>

<style scoped>
.sidebar {
  width: 240px;
  min-height: 100vh;
  background: #111827;
  color: #e5e7eb;
  display: flex;
  flex-direction: column;
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  overflow-y: auto;
  z-index: 10;
}
.logo {
  padding: 20px 16px 12px;
  border-bottom: 1px solid #1f2937;
}
.logo h1 {
  margin: 0;
  font-size: 18px;
  color: #34d399;
}
.search-box {
  padding: 12px 12px 8px;
}
.search-box input {
  width: 100%;
  padding: 7px 10px;
  border: 1px solid #374151;
  border-radius: 6px;
  background: #1f2937;
  color: #e5e7eb;
  font-size: 13px;
  box-sizing: border-box;
}
.search-box input::placeholder { color: #6b7280; }
nav { padding: 4px 0; flex: 1; }
.nav-section {
  padding: 16px 16px 4px;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #6b7280;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  color: #d1d5db;
  text-decoration: none;
  font-size: 13px;
  transition: background 0.1s;
}
.nav-item:hover { background: #1f2937; }
.nav-item.active {
  background: #1e3a5f;
  color: #93c5fd;
}
.nav-icon { width: 18px; text-align: center; font-size: 14px; }
.count {
  margin-left: auto;
  font-size: 11px;
  color: #6b7280;
  background: #1f2937;
  padding: 1px 6px;
  border-radius: 10px;
}
</style>
