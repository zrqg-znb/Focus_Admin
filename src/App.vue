<script setup lang="ts">
import { naiveI18nOptions } from '@/utils'
import { darkTheme } from 'naive-ui'
import { useAppStore } from './store'

const appStore = useAppStore()

const naiveLocale = computed(() => {
  return naiveI18nOptions[appStore.lang] ? naiveI18nOptions[appStore.lang] : naiveI18nOptions.enUS
},
)
</script>

<template>
  <div class="bg-background wh-full">
    <n-config-provider
      inline-theme-disabled :theme="appStore.colorMode === 'dark' ? darkTheme : null"
      :locale="naiveLocale.locale" :date-locale="naiveLocale.dateLocale" :theme-overrides="appStore.theme"
    >
      <naive-provider>
        <router-view />
        <Watermark :show-watermark="appStore.showWatermark" />
      </naive-provider>
    </n-config-provider>
  </div>
</template>

<style scoped>
.bg-background{
  /* 设置全局页面背景图 */
  background: url('@/assets/backgrounds/back1.jpg') no-repeat center center fixed;
  background-size: cover;
  min-height: 100vh;
}
</style>
