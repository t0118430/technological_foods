<template>
  <div class="app-layout">
    <Sidebar />
    <div class="main-area">
      <ApiKeyBanner />
      <main class="content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import Sidebar from './components/Sidebar.vue'
import ApiKeyBanner from './components/ApiKeyBanner.vue'
</script>

<style>
/* Global reset & base styles */
*, *::before, *::after {
  box-sizing: border-box;
}
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background: #ffffff;
  color: #111827;
  -webkit-font-smoothing: antialiased;
}
</style>

<style scoped>
.app-layout {
  display: flex;
  min-height: 100vh;
}
.main-area {
  flex: 1;
  margin-left: 240px;
  display: flex;
  flex-direction: column;
}
.content {
  padding: 24px 32px;
  flex: 1;
}

@media (max-width: 768px) {
  .main-area {
    margin-left: 0;
  }
}
</style>
