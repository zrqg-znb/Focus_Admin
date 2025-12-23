<script lang="ts" setup>
import type { VbenFormSchema } from '@vben/common-ui';

import { computed, markRaw, ref } from 'vue';

import { AuthenticationLogin, SliderCaptcha, z } from '@vben/common-ui';
import { $t } from '@vben/locales';

import { ElMessage } from 'element-plus';

import { getGiteeAuthorizeUrlApi } from '#/api/core';
import { useAuthStore } from '#/store';

defineOptions({ name: 'Login' });

const authStore = useAuthStore();
const loginType = ref<'account' | 'oauth'>('oauth');

const formSchema = computed((): VbenFormSchema[] => {
  return [
    {
      component: 'VbenInput',
      componentProps: {
        placeholder: $t('authentication.usernameTip'),
      },
      defaultValue: '',
      fieldName: 'username',
      label: $t('authentication.username'),
      rules: z.string().min(1, { message: $t('authentication.usernameTip') }),
    },
    {
      component: 'VbenInputPassword',
      componentProps: {
        placeholder: $t('authentication.password'),
      },
      defaultValue: '',
      fieldName: 'password',
      label: $t('authentication.password'),
      rules: z.string().min(1, { message: $t('authentication.passwordTip') }),
    },
    {
      component: markRaw(SliderCaptcha),
      fieldName: 'captcha',
      rules: z.boolean().refine((value) => value, {
        message: $t('authentication.verifyRequiredTip'),
      }),
    },
  ];
});

// Gitee OAuth 登录
async function handleGiteeLogin() {
  try {
    const data = await getGiteeAuthorizeUrlApi();
    // requestClient 配置了 responseReturn: 'body'，直接返回 data
    if (data?.authorize_url) {
      // 重定向到 Gitee 授权页面
      window.location.href = data.authorize_url;
    } else {
      ElMessage.error('获取授权链接失败');
    }
  } catch (error) {
    console.error('Gitee 登录失败:', error);
    ElMessage.error('Gitee 登录失败，请稍后重试');
  }
}

function toggleLoginType() {
  loginType.value = loginType.value === 'oauth' ? 'account' : 'oauth';
}
</script>

<template>
  <!-- OAuth2 登录模式 -->
  <div v-if="loginType === 'oauth'">
    <div class="mb-7 sm:mx-auto sm:w-full sm:max-w-md">
      <h2
        class="text-foreground mb-3 text-3xl font-bold leading-9 tracking-tight lg:text-4xl"
      >
        {{ $t('authentication.welcomeBack') }} 👋🏻
      </h2>
      <p class="text-muted-foreground lg:text-md text-sm">
        {{ $t('authentication.loginSubtitle') }}
      </p>
    </div>

    <div class="mt-8">
      <button
        type="button"
        class="flex w-full cursor-pointer items-center justify-center gap-3 rounded-lg border border-transparent bg-[#C71D23] px-5 py-3 text-base font-medium text-white shadow-sm transition-all duration-300 hover:bg-[#C71D23]/90 hover:shadow-md"
        @click="handleGiteeLogin"
      >
        <svg
          class="size-6 shrink-0"
          viewBox="0 0 1024 1024"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            d="M512 1024C229.222 1024 0 794.778 0 512S229.222 0 512 0s512 229.222 512 512-229.222 512-512 512z m259.149-568.883h-290.74a25.293 25.293 0 0 0-25.292 25.293l-0.026 63.206c0 13.952 11.315 25.293 25.267 25.293h177.024c13.978 0 25.293 11.315 25.293 25.267v12.646a75.853 75.853 0 0 1-75.853 75.853h-240.23a25.293 25.293 0 0 1-25.267-25.293V417.203a75.853 75.853 0 0 1 75.827-75.853h353.946a25.293 25.293 0 0 0 25.267-25.292l0.077-63.207a25.293 25.293 0 0 0-25.268-25.293H417.152a189.62 189.62 0 0 0-189.62 189.645V771.15c0 13.977 11.316 25.293 25.294 25.293h372.94a170.65 170.65 0 0 0 170.65-170.65V480.384a25.293 25.293 0 0 0-25.293-25.267z"
            fill="currentColor"
          />
        </svg>
        <span>Gitee OAuth2 登录</span>
      </button>
    </div>

    <div class="mt-6 text-center">
      <button
        type="button"
        class="text-muted-foreground hover:text-primary text-sm transition-colors"
        @click="toggleLoginType"
      >
        账号密码登录
      </button>
    </div>
  </div>

  <!-- 账号密码登录模式 -->
  <AuthenticationLogin
    v-else
    :form-schema="formSchema"
    :loading="authStore.loginLoading"
    :show-third-party-login="false"
    @submit="authStore.authLogin"
  >
    <template #third-party-login>
      <div class="mt-4 w-full text-center">
        <button
          type="button"
          class="text-muted-foreground hover:text-primary text-sm transition-colors"
          @click="toggleLoginType"
        >
          返回 OAuth2 登录
        </button>
      </div>
    </template>
  </AuthenticationLogin>
</template>
