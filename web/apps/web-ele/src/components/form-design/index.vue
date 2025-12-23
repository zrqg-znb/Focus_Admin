<script setup lang="ts">
import AttributePanel from './components/AttributePanel.vue';
import DesignCanvas from './components/DesignCanvas.vue';
import MaterialPanel from './components/MaterialPanel.vue';
</script>

<template>
  <div
    class="form-design-container bg-background-deep p-3 flex h-full w-full gap-3 overflow-hidden"
  >
    <!-- Left: Material Panel -->
    <div class="h-full w-64 flex-shrink-0">
      <MaterialPanel />
    </div>

    <!-- Center: Design Canvas -->
    <div class="relative h-full flex-1 overflow-hidden">
      <DesignCanvas />
    </div>

    <!-- Right: Attribute Panel -->
    <div class="h-full flex-shrink-0">
      <AttributePanel />
    </div>
  </div>
</template>

<style scoped>
.form-design-container {
  /* Ensure container takes full height relative to its parent */
  height: 100%;
}
</style>
