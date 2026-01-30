# 数据字典

数据字典模块用于管理系统中的枚举数据和配置项。

## 功能概述

- 字典类型管理
- 字典项管理
- 字典缓存

## 数据模型

```python
class Dict(CoreModel):
    """字典类型"""
    name = models.CharField(max_length=64, verbose_name="字典名称")
    code = models.CharField(max_length=64, unique=True, verbose_name="字典编码")
    status = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'sys_dict'

class DictItem(CoreModel):
    """字典项"""
    dict = models.ForeignKey(Dict, on_delete=models.CASCADE)
    label = models.CharField(max_length=64, verbose_name="标签")
    value = models.CharField(max_length=64, verbose_name="值")
    sort = models.IntegerField(default=0)
    status = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'sys_dict_item'
```

## API 接口

### 字典列表

```
GET /api/dict/list
```

### 获取字典项

```
GET /api/dict/items/{dict_code}
```

**响应示例：**

```json
{
  "code": 200,
  "data": [
    {"label": "启用", "value": "1"},
    {"label": "禁用", "value": "0"}
  ]
}
```

## 前端使用

```vue
<template>
  <el-select v-model="status">
    <el-option
      v-for="item in dictItems"
      :key="item.value"
      :label="item.label"
      :value="item.value"
    />
  </el-select>
</template>

<script setup>
import { useDict } from '@/hooks/useDict'
const { dictItems } = useDict('sys_status')
</script>
```
