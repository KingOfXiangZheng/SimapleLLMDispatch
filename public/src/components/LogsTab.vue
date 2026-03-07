<template>
  <div class="logs-tab">
    <div class="page-header">
      <div>
        <div class="page-title">调用日志</div>
        <div class="page-desc">查看最近的 API 调用记录和 Token 消耗</div>
      </div>
      <button class="btn btn-ghost" @click="$emit('refresh')">🔄 刷新</button>
    </div>

    <div class="search-bar">
      <input
        v-model="searchProvider"
        placeholder="搜索供应商..."
        @keyup.enter="doSearch"
        style="width:180px"
      >
      <input
        v-model="searchModel"
        placeholder="搜索模型..."
        @keyup.enter="doSearch"
        style="width:180px"
      >
      <button class="btn btn-primary btn-sm" @click="doSearch">搜索</button>
      <label class="flex items-center gap-1 cursor-pointer" style="margin-left:auto;font-size:0.85rem">
        <input type="checkbox" v-model="onlyErrors" @change="doSearch">
        仅显示错误
      </label>
      <button class="btn btn-ghost btn-sm" v-if="searchProvider || searchModel || onlyErrors" @click="clearSearch">清除</button>
    </div>

    <div class="card">
      <table>
        <thead>
          <tr>
            <th>时间</th>
            <th>状态</th>
            <th>供应商</th>
            <th>模型</th>
            <th>Prompt</th>
            <th>Comp.</th>
            <th>Total</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="l in logs" :key="l.id">
            <tr>
              <td style="color:var(--dim);font-size:0.8rem;white-space:nowrap">{{ l.timestamp }}</td>
              <td>
                <span :class="l.status_code === 200 ? 'badge badge-accent' : 'badge badge-red'" 
                      :title="l.error_message">
                  {{ l.status_code }}
                </span>
              </td>
              <td>{{ l.provider_name || 'N/A' }}</td>
              <td style="max-width:150px;overflow:hidden;text-overflow:ellipsis" :title="l.model">
                <span class="badge badge-ghost" style="font-size:0.75rem">{{ l.model }}</span>
              </td>
              <td>{{ (l.prompt_tokens || 0).toLocaleString() }}</td>
              <td>{{ (l.completion_tokens || 0).toLocaleString() }}</td>
              <td style="font-weight:600">{{ (l.total_tokens || 0).toLocaleString() }}</td>
            </tr>
            <tr v-if="l.status_code !== 200" class="error-detail-row">
              <td colspan="7">
                <div class="error-msg">❌ {{ l.error_message }}</div>
              </td>
            </tr>
          </template>
          <tr v-if="!logs.length">
            <td colspan="7" class="empty-row">暂无日志</td>
          </tr>
        </tbody>
      </table>
      
      <div class="pagination" v-if="paging.total_pages > 1">
        <button class="page-btn" :disabled="paging.page <= 1" @click="$emit('loadPage', 1)">«</button>
        <button class="page-btn" :disabled="paging.page <= 1" @click="$emit('loadPage', paging.page - 1)">‹</button>
        <template v-for="pg in pageNums" :key="pg">
          <button 
            class="page-btn" 
            :class="{ active: pg === paging.page }"
            @click="$emit('loadPage', pg)"
          >
            {{ pg }}
          </button>
        </template>
        <button class="page-btn" :disabled="paging.page >= paging.total_pages" @click="$emit('loadPage', paging.page + 1)">›</button>
        <button class="page-btn" :disabled="paging.page >= paging.total_pages" @click="$emit('loadPage', paging.total_pages)">»</button>
        <span class="info">共 {{ paging.total }} 条</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  logs: {
    type: Array,
    default: () => []
  },
  paging: {
    type: Object,
    default: () => ({ page: 1, total: 0, total_pages: 1, page_size: 20 })
  }
})

const emit = defineEmits(['refresh', 'loadPage', 'search'])

const searchProvider = ref('')
const searchModel = ref('')
const onlyErrors = ref(false)

function doSearch() {
  emit('search', { providerName: searchProvider.value, model: searchModel.value, onlyErrors: onlyErrors.value })
}

function clearSearch() {
  searchProvider.value = ''
  searchModel.value = ''
  onlyErrors.value = false
  emit('search', { providerName: '', model: '', onlyErrors: false })
}

function pageRange(paging) {
  const pages = []
  const total = paging.total_pages
  const cur = paging.page
  let start = Math.max(1, cur - 2)
  let end = Math.min(total, cur + 2)
  if (end - start < 4) {
    start = Math.max(1, end - 4)
    end = Math.min(total, start + 4)
  }
  for (let i = start; i <= end; i++) pages.push(i)
  return pages
}

const pageNums = computed(() => pageRange(props.paging))
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.page-title {
  font-size: 1.4rem;
  font-weight: 700;
}

.page-desc {
  font-size: 0.85rem;
  color: var(--muted);
  margin-top: 0.2rem;
}

.search-bar {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  margin-bottom: 1.25rem;
}

.error-detail-row td {
  padding-top: 0 !important;
  border-top: none !important;
}

.error-msg {
  background: #fdf2f2;
  color: #9b1c1c;
  padding: 0.5rem 0.75rem;
  border-radius: 4px;
  font-size: 0.8rem;
  margin-bottom: 0.5rem;
  word-break: break-all;
}
</style>
