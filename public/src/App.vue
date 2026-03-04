<template>
  <div class="app">
    <Sidebar :tab="tab" @update:tab="tab = $event" />
    
    <div class="main">
      <!-- Providers Tab -->
      <template v-if="tab === 'providers'">
        <ProvidersTab
          :providers="providers"
          :quota-detail="quotaDetail"
          :expanded-quota="expandedQuota"
          :paging="providerPaging"
          @add="openProviderModal()"
          @edit="openProviderModal"
          @delete="deleteProvider"
          @fetchModels="fetchModels"
          @refreshQuota="refreshQuotaDetail"
          @loadPage="loadProviders"
          @toggleQuotaDetail="toggleQuotaDetail"
        />
      </template>
      
      <!-- Groups Tab -->
      <template v-if="tab === 'groups'">
        <GroupsTab
          :groups="groups"
          @add="openGroupModal()"
          @edit="openGroupModal"
          @delete="deleteGroup"
        />
      </template>
      
      <!-- Logs Tab -->
      <template v-if="tab === 'logs'">
        <LogsTab
          :logs="logs"
          :paging="logPaging"
          @refresh="loadLogs(1)"
          @loadPage="loadLogs"
        />
      </template>
    </div>
    
    <!-- Provider Modal -->
    <ProviderModal
      ref="providerModalRef"
      :show="showProviderModal"
      :editing-provider="editingProvider"
      :initial-form="pForm"
      @close="showProviderModal = false"
      @save="saveProvider"
      @fetchModelsInModal="fetchModelsInModal"
    />
    
    <!-- Group Modal -->
    <GroupModal
      ref="groupModalRef"
      :show="showGroupModal"
      :editing-group="editingGroup"
      :initial-form="gForm"
      @close="showGroupModal = false"
      @save="saveGroup"
    />
    
    <!-- Toast -->
    <Toast ref="toastRef" />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import Sidebar from './components/Sidebar.vue'
import ProvidersTab from './components/ProvidersTab.vue'
import GroupsTab from './components/GroupsTab.vue'
import LogsTab from './components/LogsTab.vue'
import ProviderModal from './components/ProviderModal.vue'
import GroupModal from './components/GroupModal.vue'
import Toast from './components/Toast.vue'
import { useApi } from './composables/useApi'

const { 
  loadProviders: apiLoadProviders,
  saveProvider: apiSaveProvider,
  deleteProvider: apiDeleteProvider,
  getProviderQuota,
  fetchProviderModels,
  fetchModelsFromApi,
  loadGroups: apiLoadGroups,
  loadAllModels: apiLoadAllModels,
  saveGroup: apiSaveGroup,
  deleteGroup: apiDeleteGroup,
  loadLogs: apiLoadLogs
} = useApi()

const tab = ref('providers')
const toastRef = ref(null)

// Providers
const providers = ref([])
const providerPaging = reactive({ page: 1, total: 0, total_pages: 1, page_size: 20 })
const quotaDetail = reactive({})
const expandedQuota = ref(null)

// Provider Modal
const showProviderModal = ref(false)
const editingProvider = ref(null)
const providerModalRef = ref(null)

const pForm = reactive({
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

// Groups
const groups = ref([])

// Group Modal
const showGroupModal = ref(false)
const editingGroup = ref(null)
const groupModalRef = ref(null)

const gForm = reactive({
  name: '',
  alias: '',
  strategy: 'weighted_random',
  target_set: new Set(),
  model_search: '',
  allModels: [],
  _loading: false
})

// Logs
const logs = ref([])
const logPaging = reactive({ page: 1, total: 0, total_pages: 1, page_size: 50 })

// Helpers
function showToast(msg, type = 'success') {
  if (toastRef.value) {
    toastRef.value.showToast(msg, type)
  }
}

function effectiveModels(p) {
  const sm = p.selected_models
  if (!sm) return p.models
  if (!sm.length) return []
  if (typeof sm[0] === 'string') return sm
  return sm.map(s => s.model)
}

const allModels = computed(() => {
  const set = new Set()
  providers.value.forEach(p => effectiveModels(p).forEach(m => set.add(m)))
  return Array.from(set).sort()
})

// API Functions
async function loadProviders(page = 1) {
  try {
    const data = await apiLoadProviders(page, providerPaging.page_size)
    providers.value = data.items
    Object.assign(providerPaging, { 
      page: data.page, 
      total: data.total, 
      total_pages: data.total_pages 
    })
    // Auto-fetch quota for all providers
    for (const p of providers.value) {
      getProviderQuota(p.id).then(d => { quotaDetail[p.id] = d }).catch(() => {})
    }
  } catch (e) {
    showToast(e.message, 'error')
  }
}

async function loadGroups() {
  try {
    groups.value = await apiLoadGroups()
  } catch (e) {
    showToast(e.message, 'error')
  }
}

async function loadLogs(page = 1) {
  try {
    const data = await apiLoadLogs(page, logPaging.page_size)
    logs.value = data.items
    Object.assign(logPaging, { 
      page: data.page, 
      total: data.total, 
      total_pages: data.total_pages 
    })
  } catch (e) {
    showToast(e.message, 'error')
  }
}

// Provider Modal Functions
function resetPForm() {
  Object.assign(pForm, {
    name: '',
    base_url: '',
    api_key: '',
    weight: 1,
    max_requests_per_day: 1000,
    max_rpm: 0,
    max_tpm: 0,
    max_requests_total: 0,
    max_tokens_total: 0,
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
}

function openProviderModal(p = null) {
  resetPForm()
  editingProvider.value = p
  if (p) {
    pForm.name = p.name
    pForm.base_url = p.base_url
    pForm.api_key = p.api_key
    pForm.weight = p.weight
    pForm.max_requests_per_day = p.max_requests_per_day
    pForm.max_rpm = p.max_rpm || 0
    pForm.max_tpm = p.max_tpm || 0
    pForm.max_requests_total = p.max_requests_total || 0
    pForm.max_tokens_total = p.max_tokens_total || 0
    pForm.is_active = !!p.is_active
    pForm.all_models = [...p.models]
    pForm.models_text = p.models.join(', ')
    
    const sm = p.selected_models
    if (sm != null && sm.length && typeof sm[0] === 'object') {
      pForm.selected_set = new Set(sm.map(s => s.model))
      const rpd = {}, rpm = {}, tpm = {}, tr = {}, tt = {}
      sm.forEach(s => {
        rpd[s.model] = s.rpd || 0
        rpm[s.model] = s.rpm || 0
        tpm[s.model] = s.tpm || 0
        tr[s.model] = s.total_requests || 0
        tt[s.model] = s.total_tokens || 0
      })
      pForm.model_rpd = rpd
      pForm.model_rpm = rpm
      pForm.model_tpm = tpm
      pForm.model_total_requests = tr
      pForm.model_total_tokens = tt
    } else if (sm != null && sm.length) {
      pForm.selected_set = new Set(sm)
    } else if (sm == null) {
      pForm.selected_set = new Set(p.models)
    }
  }
  showProviderModal.value = true
}

async function saveProvider() {
  const models = pForm.all_models.length 
    ? pForm.all_models 
    : pForm.models_text.split(',').map(s => s.trim()).filter(Boolean)
  
  const selectedArr = pForm.all_models.length
    ? Array.from(pForm.selected_set)
    : models
    
  const selected_models = selectedArr.map(m => ({
    model: m,
    rpd: parseInt(pForm.model_rpd[m]) || 0,
    rpm: parseInt(pForm.model_rpm[m]) || 0,
    tpm: parseInt(pForm.model_tpm[m]) || 0,
    total_requests: parseInt(pForm.model_total_requests[m]) || 0,
    total_tokens: parseInt(pForm.model_total_tokens[m]) || 0
  }))
  
  const body = {
    name: pForm.name,
    base_url: pForm.base_url,
    api_key: pForm.api_key,
    models,
    selected_models,
    weight: pForm.weight,
    max_requests_per_day: pForm.max_requests_per_day,
    max_rpm: pForm.max_rpm,
    max_tpm: pForm.max_tpm,
    max_requests_total: pForm.max_requests_total,
    max_tokens_total: pForm.max_tokens_total,
    is_active: pForm.is_active
  }
  
  try {
    if (editingProvider.value) {
      await apiSaveProvider({ ...body, id: editingProvider.value.id })
    } else {
      await apiSaveProvider(body)
    }
    showProviderModal.value = false
    await loadProviders()
    showToast('供应商已保存')
  } catch (e) {
    showToast(e.message, 'error')
  }
}

async function deleteProvider(p) {
  if (!confirm(`确定删除供应商 "${p.name}"？`)) return
  try {
    await apiDeleteProvider(p.id)
    await loadProviders()
    showToast('已删除')
  } catch (e) {
    showToast(e.message, 'error')
  }
}

async function fetchModels(p) {
  p._fetching = true
  try {
    const data = await fetchProviderModels(p.id)
    await loadProviders()
    showToast(`已拉取 ${data.models.length} 个模型`)
    return data.models
  } catch (e) {
    showToast('拉取失败: ' + e.message, 'error')
  } finally {
    p._fetching = false
  }
}

async function fetchModelsInModal() {
  if (!pForm.base_url || !pForm.api_key) {
    showToast('请先填写 Base URL 和 API Key', 'error')
    return
  }
  
  pForm._fetching = true
  try {
    const fetchedModels = await fetchModelsFromApi(pForm.base_url, pForm.api_key)
    pForm.all_models = fetchedModels
    const fetchedSet = new Set(fetchedModels)
    pForm.selected_set = new Set([...pForm.selected_set].filter(m => fetchedSet.has(m)))
    showToast(`已拉取 ${fetchedModels.length} 个模型`)
  } catch (e) {
    showToast('拉取失败: ' + e.message, 'error')
  } finally {
    pForm._fetching = false
  }
}

async function toggleQuotaDetail(p) {
  if (expandedQuota.value === p.id) {
    expandedQuota.value = null
    return
  }
  expandedQuota.value = p.id
  try {
    quotaDetail[p.id] = await getProviderQuota(p.id)
  } catch (e) {
    quotaDetail[p.id] = []
    showToast('获取限额详情失败', 'error')
  }
}

async function refreshQuotaDetail(p) {
  try {
    quotaDetail[p.id] = await getProviderQuota(p.id)
  } catch (e) {
    showToast('刷新失败', 'error')
  }
}

// Auto-fetch watcher
let autoFetchTimer = null
watch([() => pForm.base_url, () => pForm.api_key], ([url, key]) => {
  if (url && key && url.startsWith('http') && key.startsWith('sk-') && !editingProvider.value) {
    clearTimeout(autoFetchTimer)
    autoFetchTimer = setTimeout(() => {
      if (pForm.all_models.length === 0) fetchModelsInModal()
    }, 1000)
  }
})

// Group Modal Functions
async function openGroupModal(g = null) {
  editingGroup.value = g
  gForm.model_search = ''
  gForm._loading = true
  gForm.allModels = []
  
  if (g) {
    gForm.name = g.name
    gForm.alias = g.alias
    gForm.strategy = g.strategy || 'weighted_random'
    gForm.target_set = new Set(g.target_models)
  } else {
    gForm.name = ''
    gForm.alias = ''
    gForm.strategy = 'weighted_random'
    gForm.target_set = new Set()
  }
  
  // Fetch fresh model list from backend first
  try {
    gForm.allModels = await apiLoadAllModels()
  } catch (e) {
    showToast('获取模型列表失败', 'error')
  } finally {
    gForm._loading = false
  }
  
  // Open modal after models are loaded
  showGroupModal.value = true
}

async function saveGroup() {
  const body = {
    name: gForm.name,
    alias: gForm.alias,
    target_models: Array.from(gForm.target_set),
    strategy: gForm.strategy
  }
  
  try {
    if (editingGroup.value) {
      await apiSaveGroup({ ...body, id: editingGroup.value.id })
    } else {
      await apiSaveGroup(body)
    }
    showGroupModal.value = false
    await Promise.all([loadGroups(), loadProviders()])
    showToast('分组已保存')
  } catch (e) {
    showToast(e.message, 'error')
  }
}

async function deleteGroup(g) {
  if (!confirm(`确定删除分组 "${g.name}"？`)) return
  try {
    await apiDeleteGroup(g.id)
    await Promise.all([loadGroups(), loadProviders()])
    showToast('已删除')
  } catch (e) {
    showToast(e.message, 'error')
  }
}

// Mount
onMounted(() => {
  loadProviders()
  loadGroups()
  loadLogs()
})
</script>

<style>
.app {
  display: flex;
  min-height: 100vh;
}

.main {
  flex: 1;
  margin-left: 240px;
  padding: 2rem 2.5rem;
  min-height: 100vh;
}
</style>
