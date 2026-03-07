<template>
  <div class="providers-tab">
    <div class="page-header">
      <div>
        <div class="page-title">供应商管理</div>
        <div class="page-desc">管理 LLM API 供应商，配置密钥、模型和配额</div>
      </div>
      <button class="btn btn-primary" @click="$emit('add')">+ 添加供应商</button>
    </div>

    <div class="search-bar">
      <input
        v-model="searchName"
        placeholder="搜索供应商名称..."
        @keyup.enter="doSearch"
        style="width:200px"
      >
      <button class="btn btn-primary btn-sm" @click="doSearch">搜索</button>
      <button class="btn btn-ghost btn-sm" v-if="searchName" @click="clearSearch">清除</button>
    </div>

    <StatsCards
      label1="供应商总数"
      :value1="stats.total"
      label2="活跃"
      :value2="stats.active"
      label3="今日总请求"
      :value3="stats.today_requests"
      label4="可用模型"
      :value4="stats.total_models"
    />

    <div class="card">
      <table>
        <thead>
          <tr>
            <th>名称</th>
            <th>Base URL</th>
            <th>已选模型</th>
            <th>限额</th>
            <th>权重</th>
            <th>状态</th>
            <th style="text-align:right">操作</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="p in providers" :key="p.id">
            <tr>
              <td style="font-weight:600">{{ p.name }}</td>
              <td 
                style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--dim)"
                :title="p.base_url"
              >
                {{ p.base_url }}
              </td>
              <td>
                <span 
                  v-for="m in effectiveModelsWithRPD(p).slice(0, 3)" 
                  :key="m.model"
                  class="badge" 
                  :class="m.consecutive_failures >= 3 ? (isModelInCooldown(m) ? 'badge-yellow' : 'badge-red') : 'badge-accent'"
                  style="margin-right:0.2rem"
                  :title="getHealthTooltip(m)"
                >
                  {{ m.model }}
                  <template v-if="m.consecutive_failures >= 3 && isModelInCooldown(m)">
                    (⏳ {{ getCooldownRemaining(m) }}s)
                  </template>
                  <template v-else-if="m.consecutive_failures >= 3">
                    (🩹 可重试)
                  </template>
                  <template v-if="m.rpd"> · {{ m.rpd }}/d</template>
                  <template v-if="m.rpm"> · {{ m.rpm }}/m</template>
                </span>
                <span 
                  class="badge badge-yellow"
                  v-if="effectiveModelsWithRPD(p).length > 3"
                >
                  +{{ effectiveModelsWithRPD(p).length - 3 }}
                </span>
              </td>
              <td style="min-width:200px;cursor:pointer" @click="toggleQuotaDetail(p)">
                <QuotaBar 
                  label="RPD" 
                  :current="p.current_requests_today" 
                  :max="p.max_requests_per_day"
                  :warning-threshold="0.8"
                  color="accent"
                />
                <QuotaBar 
                  label="RPM" 
                  :current="quotaDetail[p.id]?.provider_rpm_current || 0" 
                  :max="p.max_rpm"
                  :warning-threshold="0.8"
                  color="cyan"
                />
                <QuotaBar 
                  label="TPM" 
                  :current="quotaDetail[p.id]?.provider_tpm_current || 0" 
                  :max="p.max_tpm"
                  :warning-threshold="0.8"
                  color="yellow"
                />
                <QuotaBar 
                  label="总调" 
                  :current="quotaDetail[p.id]?.provider_total_requests_current || 0" 
                  :max="p.max_requests_total"
                  :warning-threshold="0.8"
                  color="green"
                />
                <QuotaBar 
                  label="总T" 
                  :current="quotaDetail[p.id]?.provider_total_tokens_current || 0" 
                  :max="p.max_tokens_total"
                  :warning-threshold="0.8"
                  color="accent-light"
                />
                <div style="text-align:right;margin-top:0.2rem">
                  <span style="font-size:0.68rem;color:var(--muted)">
                    {{ expandedQuota === p.id ? '▲ 收起' : '▼ 详情' }}
                  </span>
                </div>
              </td>
              <td>{{ p.weight }}</td>
              <td>
                <span class="badge" :class="p.is_active ? 'badge-green' : 'badge-red'">
                  {{ p.is_active ? '活跃' : '停用' }}
                </span>
              </td>
              <td style="text-align:right">
                <div class="actions" style="justify-content:flex-end">
                  <button 
                    class="btn btn-ghost btn-sm" 
                    v-if="effectiveModelsWithRPD(p).some(m => m.consecutive_failures > 0)"
                    @click="$emit('resetHealth', p)"
                  >
                    🩺 重置健康
                  </button>
                  <button class="btn btn-ghost btn-sm" @click="$emit('edit', p)">编辑</button>
                  <button class="btn btn-danger btn-sm" @click="$emit('delete', p)">删除</button>
                </div>
              </td>
            </tr>
            
            <!-- Expanded quota detail row -->
            <tr v-if="expandedQuota === p.id" style="background:rgba(99,102,241,0.03)">
              <td colspan="7" style="padding:0.75rem 1.25rem">
                <div v-if="!quotaDetail[p.id]" style="color:var(--muted);font-size:0.82rem">
                  加载中...
                </div>
                <div v-else>
                  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.5rem">
                    <span style="font-size:0.78rem;color:var(--muted);font-weight:600">模型限额使用情况</span>
                    <div style="display:flex;gap:0.4rem">
                      <button 
                        class="btn btn-ghost btn-sm"
                        @click.stop="$emit('fetchModels', p)" 
                        :disabled="p._fetching"
                        style="font-size:0.72rem"
                      >
                        🔄 {{ p._fetching ? '拉取中...' : '拉取模型' }}
                      </button>
                      <button 
                        class="btn btn-ghost btn-sm"
                        @click.stop="$emit('refreshQuota', p)"
                        style="font-size:0.72rem"
                      >
                        🔄 刷新
                      </button>
                    </div>
                  </div>
                  <div v-if="quotaDetail[p.id].models?.length" 
                       style="display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:0.5rem">
                    <div 
                      v-for="q in quotaDetail[p.id].models" 
                      :key="q.model"
                      style="padding:0.5rem 0.65rem;border-radius:6px;background:rgba(0,0,0,0.15)"
                    >
                      <div 
                        style="font-size:0.8rem;margin-bottom:0.35rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap"
                        :title="q.model"
                      >
                        {{ q.model }}
                      </div>
                      <QuotaBar label="RPD" :current="q.used_today" :max="q.rpd" color="green" compact />
                      <QuotaBar label="RPM" :current="q.rpm_current" :max="q.rpm" color="cyan" compact />
                      <QuotaBar label="TPM" :current="q.tpm_current || 0" :max="q.tpm" color="yellow" compact />
                      <QuotaBar label="总调" :current="q.total_requests_current || 0" :max="q.total_requests" color="green" compact />
                      <QuotaBar label="总T" :current="q.total_tokens_current || 0" :max="q.total_tokens" color="accent-light" compact />
                    </div>
                  </div>
                  <div v-else style="font-size:0.8rem;color:var(--muted)">无已选模型</div>
                </div>
              </td>
            </tr>
          </template>
          <tr v-if="!providers.length">
            <td colspan="7" class="empty-row">暂无供应商，点击右上角按钮添加</td>
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
import StatsCards from './StatsCards.vue'
import QuotaBar from './QuotaBar.vue'

const props = defineProps({
  providers: {
    type: Array,
    default: () => []
  },
  stats: {
    type: Object,
    default: () => ({ total: 0, active: 0, today_requests: 0, total_models: 0 })
  },
  quotaDetail: {
    type: Object,
    default: () => ({})
  },
  expandedQuota: {
    type: [String, Number, null],
    default: null
  },
  paging: {
    type: Object,
    default: () => ({ page: 1, total: 0, total_pages: 1, page_size: 20 })
  }
})

const $emit = defineEmits(['add', 'edit', 'delete', 'fetchModels', 'resetHealth', 'refreshQuota', 'toggleQuota', 'loadPage', 'toggleQuotaDetail', 'search'])

const searchName = ref('')

function doSearch() {
  $emit('search', { name: searchName.value })
}

function clearSearch() {
  searchName.value = ''
  $emit('search', { name: '' })
}

function effectiveModels(p) {
  const sm = p.selected_models
  if (!sm) return p.models
  if (!sm.length) return []
  if (typeof sm[0] === 'string') return sm
  return sm.map(s => s.model)
}

function effectiveModelsWithRPD(p) {
  const sm = p.selected_models
  if (!sm) return p.models.map(m => ({ model: m, rpd: 0, consecutive_failures: 0, last_failure_time: null }))
  if (!sm.length) return []
  if (typeof sm[0] === 'object') return sm
  return sm.map(m => ({ model: m, rpd: 0, consecutive_failures: 0, last_failure_time: null }))
}

function isModelInCooldown(m) {
  if (!m.last_failure_time || m.consecutive_failures < 3) return false
  const failTime = new Date(m.last_failure_time + 'Z').getTime()
  const now = new Date().getTime()
  return (now - failTime) < 300000 // 5 minutes
}

function getCooldownRemaining(m) {
  if (!m.last_failure_time) return 0
  const failTime = new Date(m.last_failure_time + 'Z').getTime()
  const now = new Date().getTime()
  const remain = Math.max(0, 300 - Math.floor((now - failTime) / 1000))
  return remain
}

function getHealthTooltip(m) {
  if (m.consecutive_failures < 3) return ''
  if (isModelInCooldown(m)) {
    return `失败次数过高 (${m.consecutive_failures})，进入 5 分钟冷却期，剩余 ${getCooldownRemaining(m)} 秒`
  }
  return `失败次数过高 (${m.consecutive_failures})，下次请求将尝试恢复`
}

const allModels = computed(() => {
  const set = new Set()
  props.providers.forEach(p => effectiveModels(p).forEach(m => set.add(m)))
  return Array.from(set).sort()
})

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

function toggleQuotaDetail(p) {
  $emit('toggleQuotaDetail', p)
}
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
</style>
