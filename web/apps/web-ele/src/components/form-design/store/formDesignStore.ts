import { defineStore } from 'pinia';
import { ref, computed, watch, nextTick } from 'vue';
import { v4 as uuidv4 } from 'uuid';

export interface FormItemSchema {
  id: string;
  type: string;
  field: string;
  label: string;
  icon?: string;
  props: Record<string, any>;
  rules?: any[];
  // 新增正则校验列表
  regList?: { pattern: string; message: string }[];
  // 显隐控制表达式，例如: model.field_abc === '1'
  showCondition?: string;
  // 是否隐藏Label
  hideLabel?: boolean;
  options?: { label: string; value: any }[];
  // 直接子项，用于 sub-table 等容器组件
  children?: FormItemSchema[];
  columns?: { span: number; children: FormItemSchema[] }[];
  // 折叠面板/标签页的子项配置
  items?: { 
    title?: string; 
    label?: string; 
    name?: string; 
    children?: FormItemSchema[];
    timestamp?: string;
    content?: string;
    type?: string;
    color?: string;
    icon?: string;
  }[];
}

export const useFormDesignStore = defineStore('form-design', () => {
  const activeId = ref<string | null>(null);
  
  const formConf = ref({
    labelWidth: 100,
    labelPosition: 'right' as 'right' | 'left' | 'top',
    size: 'default' as 'default' | 'large' | 'small',
    items: [] as FormItemSchema[]
  });

  // 历史记录相关
  const history = ref<string[]>([]);
  const historyIndex = ref(-1);
  const isTimeTravel = ref(false); // 防止 undo/redo 触发 watcher
  
  // 拖拽状态
  const isDragging = ref(false);
  const setDragging = (val: boolean) => {
    isDragging.value = val;
  };

  // 记录快照
  const recordSnapshot = () => {
    if (isTimeTravel.value) return;
    
    // 如果当前不在历史记录末尾，先删除后面的记录
    if (historyIndex.value < history.value.length - 1) {
      history.value.splice(historyIndex.value + 1);
    }
    
    history.value.push(JSON.stringify(formConf.value));
    historyIndex.value = history.value.length - 1;
    
    // 限制历史记录长度，例如最多 20 步
    if (history.value.length > 20) {
      history.value.shift();
      historyIndex.value--;
    }
  };

  // 初始化记录
  // recordSnapshot(); // 不要在定义时立即调用，因为 formConf 还是初始值，可以在 mounted 或首次变化时触发

  // 监听 formConf 变化
  watch(formConf, () => {
    recordSnapshot();
  }, { deep: true });

  const canUndo = computed(() => historyIndex.value > 0);
  const canRedo = computed(() => historyIndex.value < history.value.length - 1);

  const undo = () => {
    if (!canUndo.value) return;
    
    isTimeTravel.value = true;
    historyIndex.value--;
    const snapshot = history.value[historyIndex.value];
    if (snapshot) {
      formConf.value = JSON.parse(snapshot);
    }
    
    // 恢复选中状态 (简单处理：如果当前选中的组件在 undo 后不存在了，则取消选中)
    if (activeId.value) {
      // TODO: 检查 activeId 是否存在于新的 formConf 中
    }
    
    nextTick(() => {
      isTimeTravel.value = false;
    });
  };

  const redo = () => {
    if (!canRedo.value) return;
    
    isTimeTravel.value = true;
    historyIndex.value++;
    const snapshot = history.value[historyIndex.value];
    if (snapshot) {
      formConf.value = JSON.parse(snapshot);
    }
    
    nextTick(() => {
      isTimeTravel.value = false;
    });
  };

  function setActive(id: string | null) {
    activeId.value = id;
  }

  // 递归查找并删除
  function deleteItemFromList(items: FormItemSchema[], id: string): boolean {
    const index = items.findIndex(item => item.id === id);
    if (index > -1) {
      items.splice(index, 1);
      return true;
    }
    
    for (const item of items) {
      if (item.columns) {
        for (const col of item.columns) {
          if (deleteItemFromList(col.children, id)) {
            return true;
          }
        }
      }
      if (item.items) {
        for (const subItem of item.items) {
          if (subItem.children && deleteItemFromList(subItem.children, id)) {
            return true;
          }
        }
      }
      if (item.children) {
        if (deleteItemFromList(item.children, id)) {
          return true;
        }
      }
    }
    return false;
  }

  function deleteItem(id: string) {
    if (deleteItemFromList(formConf.value.items, id)) {
      if (activeId.value === id) {
        activeId.value = null;
      }
    }
  }
  
  function cloneComponent(origin: any) {
    const clone = JSON.parse(JSON.stringify(origin));
    
    function generateIds(item: any) {
      const id = uuidv4().replace(/-/g, '');
      item.id = id;
      item.field = `field_${id.substring(0, 8)}`;
      
      if (item.columns) {
        item.columns.forEach((col: any) => {
           col.children = col.children.map((child: any) => generateIds(child));
        });
      }
      if (item.items) {
        item.items.forEach((subItem: any) => {
           if (subItem.children) {
             subItem.children = subItem.children.map((child: any) => generateIds(child));
           }
        });
      }
      if (item.children) {
        item.children = item.children.map((child: any) => generateIds(child));
      }
      return item;
    }
    
    return generateIds(clone);
  }

  function copyItem(id: string) {
    function findAndCopy(items: FormItemSchema[]): boolean {
      const index = items.findIndex(item => item.id === id);
      if (index > -1) {
        const original = items[index];
        const clone = cloneComponent(original);
        items.splice(index + 1, 0, clone);
        activeId.value = clone.id;
        return true;
      }
      
      for (const item of items) {
        if (item.columns) {
          for (const col of item.columns) {
            if (findAndCopy(col.children)) return true;
          }
        }
        if (item.items) {
          for (const subItem of item.items) {
            if (subItem.children && findAndCopy(subItem.children)) return true;
          }
        }
        if (item.children) {
          if (findAndCopy(item.children)) return true;
        }
      }
      return false;
    }
    
    findAndCopy(formConf.value.items);
  }

  const defaultTemplates = [
    {
      title: '登录表单',
      icon: 'User',
      items: [
        {
          type: 'input',
          label: '用户名',
          props: { placeholder: '请输入用户名', width: '100%' },
          field: 'username',
          id: 'tpl_login_1'
        },
        {
          type: 'input',
          label: '密码',
          props: { placeholder: '请输入密码', type: 'password', showPassword: true, width: '100%' },
          field: 'password',
          id: 'tpl_login_2'
        }
      ]
    },
    {
      title: '注册表单',
      icon: 'Edit',
      items: [
        {
          type: 'input',
          label: '用户名',
          props: { placeholder: '请输入用户名', width: '100%' },
          field: 'username',
          id: 'tpl_reg_1'
        },
        {
          type: 'input',
          label: '密码',
          props: { placeholder: '请输入密码', type: 'password', showPassword: true, width: '100%' },
          field: 'password',
          id: 'tpl_reg_2'
        },
        {
          type: 'input',
          label: '确认密码',
          props: { placeholder: '请再次输入密码', type: 'password', showPassword: true, width: '100%' },
          field: 'confirm_password',
          id: 'tpl_reg_3'
        },
        {
          type: 'input',
          label: '手机号',
          props: { placeholder: '请输入手机号', width: '100%' },
          field: 'mobile',
          id: 'tpl_reg_4'
        }
      ]
    },
    {
      title: '用户信息',
      icon: 'Document',
      items: [
        {
          type: 'input',
          label: '姓名',
          props: { placeholder: '请输入姓名', width: '100%' },
          field: 'name',
          id: 'tpl_user_1'
        },
        {
          type: 'radio',
          label: '性别',
          props: { border: true },
          options: [{ label: '男', value: 1 }, { label: '女', value: 2 }],
          field: 'gender',
          id: 'tpl_user_2'
        },
        {
          type: 'textarea',
          label: '个人简介',
          props: { placeholder: '请输入个人简介', rows: 3, width: '100%' },
          field: 'bio',
          id: 'tpl_user_3'
        }
      ]
    }
  ];

  const templates = ref(defaultTemplates);

  const addTemplate = (template: any) => {
    templates.value.push(template);
  };

  return {
    activeId,
    formConf,
    setActive,
    deleteItem,
    cloneComponent,
    copyItem,
    undo,
    redo,
    canUndo,
    canRedo,
    isDragging,
    setDragging,
    templates,
    addTemplate
  };
});
