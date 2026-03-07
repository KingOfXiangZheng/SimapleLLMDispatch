<template>
  <div class="modal-overlay" v-if="show" @click.self="$emit('close')">
    <div class="modal">
      <h3>{{ editingGroup ? '编辑分组' : '添加分组' }}</h3>
      
      <div class="form-row">
        <div class="form-group">
          <label>分组名称</label>
          <input v-model="initialForm.name" placeholder="e.g. 高性能组">
        </div>
        <div class="form-group">
          <label>别名（对外暴露的 model 名）</label>
          <input v-model="initialForm.alias" placeholder="e.g. super-llm">
        </div>
      </div>
      
      <div class="form-row">
        <div class="form-group">
          <label>调度策略</label>
          <select v-model="initialForm.strategy">
            <option value="weighted_random">加权随机</option>
            <option value="round_robin">轮询</option>
          </select>
        </div>
      </div>

      <!-- Provider quick select -->
      <div style="margin-bottom: 1rem">
        <label style="font-size:0.8rem;color:var(--dim);font-weight:500;margin-bottom:0.5rem;display:block">
          从供应商导入模型（点击添加/取消）
        </label>
        <div class="provider-tags" v-if="providers && providers.length">
          <span 
            v-for="p in providers" 
            :key="p.id" 
            class="provider-tag"
            :class="{ 
              'provider-tag-used': isProviderUsed(p),
              'provider-tag-all': isProviderAllSelected(p) 
            }"
            @click="toggleProviderModels(p)"
            :title="isProviderAllSelected(p) ? '点击取消该供应商所有模型' : '点击添加该供应商所有模型'"
          >
            {{ p.name }} ({{ getProviderModelCount(p) }})
          </span>
        </div>
        <div v-else style="font-size:0.8rem;color:var(--muted)">
          暂无供应商，请先添加供应商
        </div>
      </div>
      
      <div>
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.75rem">
          <label style="font-size:0.8rem;color:var(--dim);font-weight:500">选择目标模型：</label>
          <input 
            v-model="initialForm.model_search" 
            placeholder="搜索模型..."
            style="padding:0.3rem 0.6rem;font-size:0.75rem;width:150px"
          >
        </div>
        
        <div v-if="initialForm._loading" style="font-size:0.82rem;color:var(--muted);padding:1rem 0;text-align:center">
          加载模型列表...
        </div>
        
        <div v-else-if="!initialForm.allModels || !initialForm.allModels.length" style="font-size:0.8rem;color:var(--muted);margin-top:0.5rem">
          暂无可用模型，请先添加供应商并拉取模型
        </div>
        
        <div v-else class="model-grid" style="margin-top:0.5rem;max-height:300px;overflow-y:auto;padding-right:4px">
          <label 
            class="model-check" 
            v-for="m in filteredAndSortedGroupModels" 
            :key="m"
            :class="{ selected: initialForm.target_set.has(m) }"
          >
            <input 
              type="checkbox" 
              :checked="initialForm.target_set.has(m)"
              @change="toggleGroupModel(m)"
            > 
            {{ m }}
          </label>
        </div>
      </div>
      
      <div class="modal-actions">
        <button class="btn btn-ghost" @click="$emit('close')">取消</button>
        <button class="btn btn-primary" @click="$emit('save')">保存</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  show: Boolean,
  editingGroup: Object,
  initialForm: Object,
  providers: {
    type: Array,
    default: () => []
  }
})

function getProviderModelCount(provider) {
  const sm = provider.selected_models
  if (!sm) return (provider.models || []).length
  if (!sm.length) return 0
  if (typeof sm[0] === 'string') return sm.length
  return sm.length
}

function getProviderModels(provider) {
  const sm = provider.selected_models
  if (!sm || !sm.length) {
    return provider.models || []
  }
  if (typeof sm[0] === 'string') return sm
  return sm.map(s => s.model)
}

function isProviderUsed(provider) {
  if (!props.initialForm) return false
  const models = getProviderModels(provider)
  if (!models.length) return false
  const currentSet = props.initialForm.target_set
  return models.some(m => currentSet.has(m))
}

function isProviderAllSelected(provider) {
  if (!props.initialForm) return false
  const models = getProviderModels(provider)
  if (!models.length) return false
  const currentSet = props.initialForm.target_set
  return models.every(m => currentSet.has(m))
}

function toggleProviderModels(provider) {
  if (!props.initialForm) return
  
  const models = getProviderModels(provider)
  if (!models.length) return
  
  const currentSet = props.initialForm.target_set
  const allSelected = models.every(m => currentSet.has(m))
  
  const newSet = new Set(currentSet)
  if (allSelected) {
    models.forEach(m => newSet.delete(m))
  } else {
    models.forEach(m => newSet.add(m))
  }
  
  props.initialForm.target_set = newSet
}

const filteredAndSortedGroupModels = computed(() => {
  if (!props.initialForm || !props.initialForm.allModels) return []
  let list = props.initialForm.allModels.filter(m =>
    m.toLowerCase().includes((props.initialForm.model_search || '').toLowerCase())
  )
  return list.sort((a, b) => {
    const aSel = props.initialForm.target_set.has(a) ? 1 : 0
    const bSel = props.initialForm.target_set.has(b) ? 1 : 0
    if (aSel !== bSel) return bSel - aSel
    return a.localeCompare(b)
  })
})

function toggleGroupModel(m) {
  if (!props.initialForm) return
  if (props.initialForm.target_set.has(m)) {
    props.initialForm.target_set.delete(m)
  } else {
    props.initialForm.target_set.add(m)
  }
  props.initialForm.target_set = new Set(props.initialForm.target_set)
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.65);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal {
  background: var(--surface);
  border-radius: var(--radius);
  padding: 1.75rem;
  width: 580px;
  max-width: 95vw;
  max-height: 85vh;
  overflow-y: auto;
  border: 1px solid var(--border);
  box-shadow: 0 25px 60px rgba(0, 0, 0, 0.5);
}

.modal h3 {
  margin-bottom: 1.25rem;
  font-size: 1.1rem;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.6rem;
  margin-top: 1.25rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border);
}

.provider-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.provider-tag {
  display: inline-block;
  padding: 0.35rem 0.65rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border);
  border-radius: 4px;
  font-size: 0.8rem;
  color: var(--muted);
  cursor: pointer;
  transition: all 0.2s;
}

.provider-tag:hover {
  background: rgba(255, 255, 255, 0.1);
  color: var(--dim);
}

.provider-tag-used {
  background: rgba(99, 102, 241, 0.15);
  border-color: var(--accent);
  color: var(--accent);
}

.provider-tag-used:hover {
  background: rgba(99, 102, 241, 0.25);
  color: var(--accent);
}

.provider-tag-all {
  border-width: 2px;
  font-weight: 600;
}
</style>
