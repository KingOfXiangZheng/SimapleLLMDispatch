<template>
  <div class="groups-tab">
    <div class="page-header">
      <div>
        <div class="page-title">模型分组</div>
        <div class="page-desc">将多个模型聚合为一个别名，统一调度</div>
      </div>
      <button class="btn btn-primary" @click="$emit('add')">+ 添加分组</button>
    </div>

    <div class="search-bar">
      <input
        v-model="searchName"
        placeholder="搜索名称或别名..."
        @keyup.enter="doSearch"
        style="width:200px"
      >
      <button class="btn btn-primary btn-sm" @click="doSearch">搜索</button>
      <button class="btn btn-ghost btn-sm" v-if="searchName" @click="clearSearch">清除</button>
    </div>

    <div class="card">
      <table>
        <thead>
          <tr>
            <th>名称</th>
            <th>别名</th>
            <th>目标模型</th>
            <th>调度策略</th>
            <th style="text-align:right">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="g in groups" :key="g.id">
            <td style="font-weight:600">{{ g.name }}</td>
            <td><span class="badge badge-cyan">{{ g.alias }}</span></td>
            <td>
              <span 
                class="badge badge-accent" 
                v-for="m in (g.target_models || []).slice(0, 3)" 
                :key="m"
                style="margin-right:0.2rem"
              >
                {{ m }}
              </span>
              <span 
                class="badge badge-yellow"
                v-if="(g.target_models || []).length > 3"
              >
                +{{ g.target_models.length - 3 }}
              </span>
            </td>
            <td>
              <span class="badge" :class="g.strategy === 'round_robin' ? 'badge-yellow' : 'badge-green'">
                {{ g.strategy === 'round_robin' ? '轮询' : '加权随机' }}
              </span>
            </td>
            <td style="text-align:right">
              <div class="actions" style="justify-content:flex-end">
                <button class="btn btn-ghost btn-sm" @click="$emit('edit', g)">编辑</button>
                <button class="btn btn-danger btn-sm" @click="$emit('delete', g)">删除</button>
              </div>
            </td>
          </tr>
          <tr v-if="!groups.length">
            <td colspan="5" class="empty-row">暂无分组，点击右上角按钮添加</td>
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
          >{{ pg }}</button>
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
  groups: { type: Array, default: () => [] },
  paging: { type: Object, default: () => ({ page: 1, total: 0, total_pages: 1, page_size: 20 }) }
})

const emit = defineEmits(['add', 'edit', 'delete', 'loadPage', 'search'])

const searchName = ref('')

function doSearch() {
  emit('search', { name: searchName.value })
}

function clearSearch() {
  searchName.value = ''
  emit('search', { name: '' })
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
.page-title { font-size: 1.4rem; font-weight: 700; }
.page-desc { font-size: 0.85rem; color: var(--muted); margin-top: 0.2rem; }
.search-bar { display: flex; gap: 0.5rem; align-items: center; margin-bottom: 1.25rem; }
</style>
