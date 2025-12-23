<script setup lang="ts">
import { Page } from '@vben/common-ui';

import FolderTree from './components/FolderTree.vue';
import FileList from './components/FileList.vue';
import FileToolbar from './components/FileToolbar.vue';
import CreateFolderDialog from './components/CreateFolderDialog.vue';
</script>

<template>
  <Page auto-content-height>
    <div class="flex gap-3 h-full w-full ">
      <FolderTree />
      <div class="flex flex-1 flex-col overflow-hidden bg-background rounded-[10px]">
         <FileToolbar />
         <div class="flex-1 overflow-hidden">
           <FileList />
         </div>
      </div>
      <CreateFolderDialog />
    </div>
  </Page>
</template>
