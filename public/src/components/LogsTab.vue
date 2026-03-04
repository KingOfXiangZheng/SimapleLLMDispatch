<template>
  <div class="logs-tab">
    <div class="page-header">
      <div>
        <div class="page-title">调用日志</div>
        <div class="page-desc">查看最近的 API 调用记录和 Token 消耗</div>
      </div>
      <button class="btn btn-ghost" @click="$emit('refresh')">🔄 刷新</button>
    </div>

    <div class="card">
      <table>
        <thead>
          <tr>
            <th>时间</th>
            <th>供应商</th>
            <th>模型</th>
            <th>Prompt Tokens</th>
            <th>Completion Tokens</th>
            <th>Total</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="l in logs" :key="l.id">
            <td style="color:var(--dim);font-size:0.8rem">{{ l.timestamp }}</td>
            <td>{{ l.provider_name || 'N/A' }}</td>
            <td><span class="badge badge-accent">{{ l.model }}</span></td>
            <td>{{ (l.prompt_tokens || 0).toLocaleString() }}</td>
            <td>{{ (l.completion_tokens || 0).toLocaleString() }}</td>
            <td style="font-weight:600">{{ (l.total_tokens || 0).toLocaleString() }}</td>
          </tr>
          <tr v-if="!logs.length">
            <td colspan="6" class="empty-row">暂无日志</td>
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
import { computed } from 'vue'

const props = defineProps({
  logs: {
    type: Array,
    default: () => []
  },
  paging: {
    type: Object,
    default: () => ({ page: 1, total: 0, total_pages: 1, page_size: 50 })
  }
})

defineEmits(['refresh', 'loadPage'])

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
  margin-bottom: 1.75rem;
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
</style>
