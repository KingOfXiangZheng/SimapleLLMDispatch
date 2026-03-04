<template>
  <div :class="compact ? 'quota-bar-compact' : 'quota-bar'">
    <span v-if="!compact" style="font-size:0.7rem;color:var(--muted);width:28px">{{ label }}</span>
    <span v-else style="font-size:0.7rem;color:var(--muted);width:30px">{{ label }}</span>
    <div :class="compact ? 'quota-track-compact' : 'quota-track'" :style="{ flex: 1 }">
      <div 
        class="quota-fill" 
        :style="{
          width: max ? Math.min(100, current / max * 100) + '%' : '0%',
          background: max && (current / max) > warningThreshold ? 'var(--red)' : `var(--${color})`
        }"
      ></div>
    </div>
    <span 
      :class="compact ? 'quota-text-compact' : 'quota-text'"
      :style="{ minWidth: compact ? '50px' : '55px', textAlign: 'right' }"
    >
      {{ formatNumber(current) }}/{{ max ? formatNumber(max) : '∞' }}
    </span>
  </div>
</template>

<script setup>
defineProps({
  label: String,
  current: {
    type: Number,
    default: 0
  },
  max: {
    type: Number,
    default: 0
  },
  warningThreshold: {
    type: Number,
    default: 0.8
  },
  color: {
    type: String,
    default: 'accent'
  },
  compact: {
    type: Boolean,
    default: false
  }
})

function formatNumber(num) {
  if (num === undefined || num === null) return '-'
  return num.toLocaleString()
}
</script>

<style scoped>
.quota-bar {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin-bottom: 0.3rem;
}

.quota-bar-compact {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.25rem;
}

.quota-track {
  flex: 1;
  height: 6px;
  background: var(--bg);
  border-radius: 3px;
  overflow: hidden;
  min-width: 60px;
}

.quota-track-compact {
  flex: 1;
  height: 6px;
  background: var(--bg);
  border-radius: 3px;
  overflow: hidden;
}

.quota-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s;
}

.quota-text {
  font-size: 0.78rem;
  color: var(--dim);
  white-space: nowrap;
}

.quota-text-compact {
  font-size: 0.73rem;
  color: var(--dim);
  white-space: nowrap;
}
</style>
