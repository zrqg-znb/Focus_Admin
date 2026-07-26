<script setup lang="ts">
defineOptions({ name: 'AgentToolsPageShell' });
</script>

<template>
  <main class="agent-tools-page-shell">
    <slot></slot>
  </main>
</template>

<style scoped>
.agent-tools-page-shell {
  display: flex;
  min-height: 100%;
  flex-direction: column;
  padding: 16px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  background: var(--el-bg-color);
  box-shadow: 0 2px 10px rgb(15 23 42 / 5%);
}

@media (max-width: 760px) {
  .agent-tools-page-shell {
    padding: 12px;
  }
}
</style>
