// https://vitepress.dev/guide/custom-theme
import type { EnhanceAppContext, Theme } from 'vitepress';

import DefaultTheme from 'vitepress/theme';

import {
  FocusApiTable,
  FocusHome,
  FocusModuleGrid,
  FocusModuleHero,
  FocusModuleSection,
} from '../components';
import SiteLayout from './components/site-layout.vue';
import { initHmPlugin } from './plugins/hm';

import './styles';

import 'virtual:group-icons.css';

export default {
  async enhanceApp(ctx: EnhanceAppContext) {
    const { app } = ctx;
    app.component('FocusApiTable', FocusApiTable);
    app.component('FocusHome', FocusHome);
    app.component('FocusModuleGrid', FocusModuleGrid);
    app.component('FocusModuleHero', FocusModuleHero);
    app.component('FocusModuleSection', FocusModuleSection);

    // 百度统计
    initHmPlugin();
  },
  extends: DefaultTheme,
  Layout: SiteLayout,
} satisfies Theme;
