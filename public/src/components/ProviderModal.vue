<template>
  <div class="modal-overlay" v-if="show" @click.self="$emit('close')">
    <div class="modal">
      <h3>{{ editingProvider ? '编辑供应商' : '添加供应商' }}</h3>
      
      <div class="form-row">
        <div class="form-group">
          <label>名称</label>
          <input v-model="form.name" placeholder="e.g. DeepSeek">
        </div>
        <div class="form-group">
          <label>权重</label>
          <input v-model.number="form.weight" type="number" min="1">
        </div>
      </div>
      
      <div class="form-row">
        <div class="form-group" style="flex:2">
          <label>Base URL</label>
          <input v-model="form.base_url" placeholder="https://api.deepseek.com/v1">
        </div>
      </div>
      
      <div class="form-row">
        <div class="form-group">
          <label>API Key</label>
          <input v-model="form.api_key" type="password" placeholder="sk-...">
        </div>
      </div>
      
      <div style="margin-bottom:0.85rem">
        <label style="font-size:0.78rem;color:var(--dim);font-weight:500;margin-bottom:0.5rem;display:block">
          速率限制预设
        </label>
        <div style="display:flex;gap:0.4rem;flex-wrap:wrap">
          <button 
            class="btn btn-ghost btn-sm" 
            v-for="preset in ratePresets" 
            :key="preset.label"
            @click="applyPreset(preset)"
          >
            {{ preset.label }}
          </button>
        </div>
      </div>
      
      <div class="form-row">
        <div class="form-group">
          <label>每日请求 (RPD)，0=不限</label>
          <input v-model.number="form.max_requests_per_day" type="number" min="0">
        </div>
        <div class="form-group">
          <label>每分钟请求 (RPM)，0=不限</label>
          <input v-model.number="form.max_rpm" type="number" min="0">
        </div>
        <div class="form-group">
          <label>每分钟 Token (TPM)，0=不限</label>
          <input v-model.number="form.max_tpm" type="number" min="0">
        </div>
      </div>
      
      <div class="form-row">
        <div class="form-group">
          <label>总调用次数，0=不限</label>
          <input v-model.number="form.max_requests_total" type="number" min="0">
        </div>
        <div class="form-group">
          <label>总 Token，0=不限</label>
          <input v-model.number="form.max_tokens_total" type="number" min="0">
        </div>
      </div>
      
      <div class="form-row">
        <div class="form-group">
          <label>模型（逗号分隔，或保存后使用"拉取模型"自动获取）</label>
          <div style="display:flex;gap:0.5rem">
            <input v-model="form.models_text" placeholder="gpt-4, gpt-3.5-turbo" style="flex:1">
            <button 
              class="btn btn-ghost" 
              @click="$emit('fetchModelsInModal')"
              :disabled="form._fetching"
            >
              {{ form._fetching ? '...' : '拉取模型' }}
            </button>
          </div>
        </div>
      </div>
      
      <div v-if="form.all_models.length" style="margin-top:0.75rem">
        <label style="font-size:0.8rem;color:var(--dim);font-weight:500">
          选择要启用的模型（可设置每模型限额，0=不限/继承）：
        </label>
        <div style="margin:0.5rem 0;display:flex;gap:0.5rem;align-items:center">
          <button class="btn btn-ghost btn-sm" @click="selectAll">全选</button>
          <button class="btn btn-ghost btn-sm" @click="selectNone">全不选</button>
          <div style="flex:1"></div>
          <input 
            v-model="form.model_search" 
            placeholder="搜索模型..."
            style="padding:0.3rem 0.6rem;font-size:0.75rem;width:150px"
          >
        </div>
        <div style="display:flex;flex-direction:column;gap:6px;max-height:400px;overflow-y:auto;padding-right:6px">
          <div 
            v-for="m in filteredAndSortedModels" 
            :key="m"
            :style="{
              borderRadius: '8px',
              border: form.selected_set.has(m) ? '1px solid var(--accent)' : '1px solid var(--border)',
              background: form.selected_set.has(m) ? 'rgba(99,102,241,0.07)' : 'rgba(255,255,255,0.02)',
              overflow: 'visible',
              transition: 'all 0.2s'
            }"
          >
            <div style="display:flex;align-items:center;gap:10px;padding:8px 12px;cursor:pointer;" @click="toggleModel(m)">
              <input 
                type="checkbox" 
                :checked="form.selected_set.has(m)"
                @click.stop="toggleModel(m)"
                style="width:15px;height:15px;flex-shrink:0;cursor:pointer;margin:0;padding:0;accent-color:var(--accent)"
              >
              <span 
                style="flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:13px;color:#f1f5f9;font-weight:500;line-height:1.4"
                :title="m"
              >
                {{ m }}
              </span>
            </div>
            <div v-if="form.selected_set.has(m)"
                style="display:grid;grid-template-columns:repeat(5,1fr);gap:8px;padding:10px 12px;border-top:1px solid var(--border);background:rgba(0,0,0,0.15)"
            >
              <div style="display:flex;flex-direction:column;align-items:center;gap:0.15rem">
                <label style="font-size:0.65rem;color:var(--muted)">RPD</label>
                <input 
                  type="number" 
                  min="0" 
                  :value="form.model_rpd[m] || 0"
                  @input="form.model_rpd[m] = parseInt($event.target.value) || 0"
                  style="width:100%;padding:0.3rem 0.25rem;font-size:0.78rem;text-align:center"
                >
              </div>
              <div style="display:flex;flex-direction:column;align-items:center;gap:0.15rem">
                <label style="font-size:0.65rem;color:var(--muted)">RPM</label>
                <input 
                  type="number" 
                  min="0" 
                  :value="form.model_rpm[m] || 0"
                  @input="form.model_rpm[m] = parseInt($event.target.value) || 0"
                  style="width:100%;padding:0.3rem 0.25rem;font-size:0.78rem;text-align:center"
                >
              </div>
              <div style="display:flex;flex-direction:column;align-items:center;gap:0.15rem">
                <label style="font-size:0.65rem;color:var(--muted)">TPM</label>
                <input 
                  type="number" 
                  min="0" 
                  :value="form.model_tpm[m] || 0"
                  @input="form.model_tpm[m] = parseInt($event.target.value) || 0"
                  style="width:100%;padding:0.3rem 0.25rem;font-size:0.78rem;text-align:center"
                >
              </div>
              <div style="display:flex;flex-direction:column;align-items:center;gap:0.15rem">
                <label style="font-size:0.65rem;color:var(--muted)">总调用</label>
                <input 
                  type="number" 
                  min="0" 
                  :value="form.model_total_requests[m] || 0"
                  @input="form.model_total_requests[m] = parseInt($event.target.value) || 0"
                  style="width:100%;padding:0.3rem 0.25rem;font-size:0.78rem;text-align:center"
                >
              </div>
              <div style="display:flex;flex-direction:column;align-items:center;gap:0.15rem">
                <label style="font-size:0.65rem;color:var(--muted)">总Token</label>
                <input 
                  type="number" 
                  min="0" 
                  :value="form.model_total_tokens[m] || 0"
                  @input="form.model_total_tokens[m] = parseInt($event.target.value) || 0"
                  style="width:100%;padding:0.3rem 0.25rem;font-size:0.78rem;text-align:center"
                >
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <div v-if="editingProvider" style="margin-top:1rem">
        <label class="model-check" style="font-size:0.85rem">
          <input type="checkbox" v-model="form.is_active"> 启用此供应商
        </label>
      </div>
      
      <div class="modal-actions">
        <button class="btn btn-ghost" @click="$emit('close')">取消</button>
        <button class="btn btn-primary" @click="$emit('save')">保存</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, computed, watch } from 'vue'

const props = defineProps({
  show: Boolean,
  editingProvider: Object,
  initialForm: Object
})

const emit = defineEmits(['close', 'save', 'fetchModelsInModal'])

const ratePresets = [
  { label: 'OpenAI Free', rpd: 200, rpm: 3, tpm: 40000 },
  { label: 'OpenAI Tier1', rpd: 10000, rpm: 500, tpm: 200000 },
  { label: 'OpenAI Tier2', rpd: 0, rpm: 5000, tpm: 2000000 },
  { label: 'Claude Free', rpd: 100, rpm: 5, tpm: 20000 },
  { label: 'Claude Tier1', rpd: 10000, rpm: 50, tpm: 40000 },
  { label: 'DeepSeek', rpd: 0, rpm: 60, tpm: 0 },
  { label: 'Gemini Free', rpd: 1500, rpm: 15, tpm: 32000 },
  { label: '不限制', rpd: 0, rpm: 0, tpm: 0 },
]

const form = reactive({
  name: '',
  base_url: '',
  api_key: '',
  weight: 1,
  max_requests_per_day: 1000,
  max_rpm: 0,
  max_tpm: 0,
  max_requests_total: 0,
  max_tokens_total: 0,
  models_text: '',
  all_models: [],
  model_search: '',
  selected_set: new Set(),
  model_rpd: {},
  model_rpm: {},
  model_tpm: {},
  model_total_requests: {},
  model_total_tokens: {},
  is_active: true,
  _fetching: false
})

const filteredAndSortedModels = computed(() => {
  let list = form.all_models.filter(m =>
    m.toLowerCase().includes(form.model_search.toLowerCase())
  )
  return list.sort((a, b) => {
    const aSel = form.selected_set.has(a) ? 1 : 0
    const bSel = form.selected_set.has(b) ? 1 : 0
    if (aSel !== bSel) return bSel - aSel
    return a.localeCompare(b)
  })
})

function applyPreset(preset) {
  form.max_requests_per_day = preset.rpd
  form.max_rpm = preset.rpm
  form.max_tpm = preset.tpm
}

function toggleModel(m) {
  if (form.selected_set.has(m)) {
    form.selected_set.delete(m)
  } else {
    form.selected_set.add(m)
  }
  form.selected_set = new Set(form.selected_set)
}

function selectAll() {
  form.selected_set = new Set(form.all_models)
}

function selectNone() {
  form.selected_set = new Set()
}

// Watch for initialForm changes to update form
watch(() => props.initialForm, (newForm) => {
  if (newForm) {
    Object.assign(form, newForm)
    if (newForm.selected_set instanceof Set) {
      form.selected_set = new Set(newForm.selected_set)
    }
  }
}, { immediate: true, deep: true })

defineExpose({ form, ratePresets, applyPreset, toggleModel, selectAll, selectNone })
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
</style>
