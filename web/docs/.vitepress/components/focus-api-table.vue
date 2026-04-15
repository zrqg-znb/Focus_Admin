<script lang="ts" setup>
interface ApiItem {
  method: 'DELETE' | 'GET' | 'PATCH' | 'POST' | 'PUT';
  path: string;
  purpose: string;
  params: string;
  returns: string;
  consumer: string;
}

defineProps<{
  items: ApiItem[];
}>();
</script>

<template>
  <div class="focus-api-table">
    <table>
      <thead>
        <tr>
          <th>Method / Path</th>
          <th>用途</th>
          <th>关键参数</th>
          <th>主要返回</th>
          <th>前端消费页 / 场景</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in items" :key="`${item.method}:${item.path}`">
          <td class="focus-api-table__path">
            <span :class="['focus-method', `is-${item.method.toLowerCase()}`]">
              {{ item.method }}
            </span>
            <code>{{ item.path }}</code>
          </td>
          <td>{{ item.purpose }}</td>
          <td>{{ item.params }}</td>
          <td>{{ item.returns }}</td>
          <td>{{ item.consumer }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
