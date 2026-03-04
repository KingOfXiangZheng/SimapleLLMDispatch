<template>
  <div class="groups-tab">
    <div class="page-header">
      <div>
        <div class="page-title">模型分组</div>
        <div class="page-desc">将多个模型聚合为一个别名，统一调度</div>
      </div>
      <button class="btn btn-primary" @click="$emit('add')">+ 添加分组</button>
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
              <span class="badge badge-accent" v-for="m in g.target_models" :key="m">{{ m }}</span>
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
    </div>
  </div>
</template>

<script setup>
defineProps({
  groups: {
    type: Array,
    default: () => []
  }
})

defineEmits(['add', 'edit', 'delete'])
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
