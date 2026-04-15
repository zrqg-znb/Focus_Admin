<script lang="ts" setup>
import type { FocusModuleMeta } from '../../src/data/modules';

defineProps<{
  module: FocusModuleMeta;
}>();
</script>

<template>
  <header class="focus-module-hero">
    <div class="focus-module-hero__content">
      <p class="focus-kicker">Focus Product Module</p>
      <h1>{{ module.title }}</h1>
      <p class="focus-module-hero__summary">
        {{ module.summary }}
      </p>
      <p class="focus-module-hero__tagline">
        {{ module.tagline }}
      </p>

      <div class="focus-module-hero__tags">
        <span v-for="alias in module.aliases" :key="alias">{{ alias }}</span>
      </div>

      <div class="focus-module-hero__highlights">
        <article v-for="highlight in module.highlights" :key="highlight">
          <span>Key Point</span>
          <p>{{ highlight }}</p>
        </article>
      </div>
    </div>

    <aside class="focus-module-hero__meta">
      <div>
        <span>后端前缀</span>
        <code>{{ module.backendPrefixes.join(' / ') }}</code>
      </div>
      <div>
        <span>前端入口</span>
        <code>{{ module.frontendRoutes.join(' / ') }}</code>
      </div>
      <div>
        <span>相关实现</span>
        <span>{{ module.apiFiles.length }} 个 API 文件 / {{ module.viewDirs.length }} 个视图目录</span>
      </div>
      <div>
        <span>主要使用者</span>
        <span>{{ module.audience.join('、') }}</span>
      </div>
      <div>
        <span>相关文档</span>
        <div class="focus-module-hero__links">
          <a v-for="item in module.relatedDocs" :key="item.link" :href="item.link">
            {{ item.label }}
          </a>
        </div>
      </div>
    </aside>
  </header>
</template>
