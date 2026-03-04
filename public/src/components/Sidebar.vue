<template>
  <nav class="sidebar">
    <div class="sidebar-brand">
      <div>
        <span class="icon">⚡</span>
        <span class="title">SimapleLLMDispatch</span>
        <div class="sub">智能调度中心</div>
      </div>
    </div>
    
    <a 
      class="nav-item" 
      :class="{ active: tab === 'providers' }" 
      @click="$emit('update:tab', 'providers')"
    >
      <span class="emoji">📡</span> 供应商管理
    </a>
    
    <a 
      class="nav-item" 
      :class="{ active: tab === 'groups' }" 
      @click="$emit('update:tab', 'groups')"
    >
      <span class="emoji">📦</span> 模型分组
    </a>
    
    <a 
      class="nav-item" 
      :class="{ active: tab === 'logs' }" 
      @click="$emit('update:tab', 'logs')"
    >
      <span class="emoji">📊</span> 调用日志
    </a>
    
    <a 
      class="nav-item" 
      href="https://github.com/KingOfXiangZheng/SimapleLLMDispatch" 
      target="_blank"
      rel="noopener noreferrer"
    >
      <span class="emoji">🐙</span> 关于 / GitHub
    </a>

    <div class="sidebar-footer">
      <div class="endpoint-label">统一入口</div>
      <div class="endpoint">http://localhost:3000/v1</div>
    </div>
  </nav>
</template>

<script setup>
defineProps({
  tab: {
    type: String,
    required: true
  }
})

defineEmits(['update:tab'])
</script>

<style scoped>
.sidebar {
  width: 240px;
  background: var(--surface);
  border-right: 1px solid var(--border);
  padding: 1.75rem 0;
  flex-shrink: 0;
  position: fixed;
  top: 0;
  left: 0;
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.sidebar-brand {
  padding: 0 1.5rem 1.75rem;
  display: flex;
  align-items: center;
  gap: 0.6rem;
  border-bottom: 1px solid var(--border);
  margin-bottom: 0.75rem;
}

.sidebar-brand .icon {
  font-size: 1.5rem;
}

.sidebar-brand .title {
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--text);
}

.sidebar-brand .sub {
  font-size: 0.7rem;
  color: var(--muted);
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  padding: 0.65rem 1.5rem;
  color: var(--dim);
  text-decoration: none;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.15s;
  border-left: 3px solid transparent;
  margin: 0.1rem 0;
}

.nav-item:hover {
  color: var(--text);
  background: rgba(99, 102, 241, 0.06);
}

.nav-item.active {
  color: var(--accent-light);
  background: var(--accent-glow);
  border-left-color: var(--accent);
  font-weight: 600;
}

.nav-item .emoji {
  font-size: 1.1rem;
  width: 1.5rem;
  text-align: center;
}

.sidebar-footer {
  margin-top: auto;
  padding: 1rem 1.5rem;
  border-top: 1px solid var(--border);
}

.sidebar-footer .endpoint {
  font-size: 0.75rem;
  color: var(--muted);
  background: var(--bg);
  padding: 0.5rem 0.65rem;
  border-radius: var(--radius-sm);
  font-family: 'SF Mono', 'Fira Code', monospace;
  word-break: break-all;
}

.sidebar-footer .endpoint-label {
  font-size: 0.7rem;
  color: var(--muted);
  margin-bottom: 0.35rem;
}
</style>
