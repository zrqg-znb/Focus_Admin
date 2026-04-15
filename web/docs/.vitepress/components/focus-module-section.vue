<script lang="ts" setup>
defineProps<{
  title: string;
  kicker?: string;
  summary?: string;
}>();
</script>

<template>
  <section class="focus-module-section">
    <header class="focus-module-section__header">
      <p v-if="kicker" class="focus-kicker">{{ kicker }}</p>
      <h2>{{ title }}</h2>
      <p v-if="summary" class="focus-module-section__summary">{{ summary }}</p>
    </header>
    <div class="focus-module-section__body">
      <slot />
    </div>
  </section>
</template>
