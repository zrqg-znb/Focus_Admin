<script lang="ts" setup>
import { computed } from 'vue';

import {
  focusModuleGroupLabels,
  focusModules,
} from '../../src/data/modules';

const props = withDefaults(
  defineProps<{
    grouped?: boolean;
    slugs?: string[];
  }>(),
  {
    grouped: true,
    slugs: undefined,
  },
);

const modules = computed(() => {
  if (!props.slugs?.length) {
    return focusModules;
  }

  return focusModules.filter((item) => props.slugs?.includes(item.slug));
});

const groupedModules = computed(() => {
  return Object.entries(focusModuleGroupLabels)
    .map(([group, label]) => ({
      group,
      items: modules.value.filter((item) => item.group === group),
      label,
    }))
    .filter((entry) => entry.items.length > 0);
});
</script>

<template>
  <div class="focus-module-grid">
    <template v-if="grouped">
      <section
        v-for="entry in groupedModules"
        :key="entry.group"
        class="focus-module-grid__group"
      >
        <div class="focus-module-grid__header">
          <p class="focus-kicker">Module Lane</p>
          <h2>{{ entry.label }}</h2>
        </div>
        <div class="focus-module-grid__cards">
          <a
            v-for="module in entry.items"
            :key="module.slug"
            :href="`/modules/${module.slug}`"
            class="focus-module-card"
          >
            <div class="focus-module-card__topline">
              <span>{{ module.title }}</span>
              <span>{{ module.titleEn }}</span>
            </div>
            <p class="focus-module-card__tagline">{{ module.tagline }}</p>
            <p class="focus-module-card__summary">{{ module.summary }}</p>
            <ul class="focus-module-card__highlights">
              <li v-for="highlight in module.highlights.slice(0, 3)" :key="highlight">
                {{ highlight }}
              </li>
            </ul>
            <div class="focus-module-card__meta">
              <span>{{ module.backendPrefixes[0] }}</span>
              <span>{{ module.frontendRoutes[0] }}</span>
            </div>
            <div class="focus-module-card__audience">
              <strong>适用角色</strong>
              <span>{{ module.audience.join(' / ') }}</span>
            </div>
          </a>
        </div>
      </section>
    </template>
    <div v-else class="focus-module-grid__cards">
      <a
        v-for="module in modules"
        :key="module.slug"
        :href="`/modules/${module.slug}`"
        class="focus-module-card"
      >
        <div class="focus-module-card__topline">
          <span>{{ module.title }}</span>
          <span>{{ module.titleEn }}</span>
        </div>
        <p class="focus-module-card__tagline">{{ module.tagline }}</p>
        <p class="focus-module-card__summary">{{ module.summary }}</p>
        <div class="focus-module-card__meta">
          <span>{{ module.backendPrefixes[0] }}</span>
          <span>{{ module.frontendRoutes[0] }}</span>
        </div>
      </a>
    </div>
  </div>
</template>
