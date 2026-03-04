<template>
  <div class="stats">
    <div class="stat-card">
      <div class="label">{{ label1 }}</div>
      <div class="value">{{ value1 }}</div>
    </div>
    <div class="stat-card">
      <div class="label">{{ label2 }}</div>
      <div class="value" style="color: var(--green)">{{ value2 }}</div>
    </div>
    <div class="stat-card">
      <div class="label">{{ label3 }}</div>
      <div class="value" style="color: var(--cyan)">{{ value3 }}</div>
    </div>
    <div class="stat-card">
      <div class="label">{{ label4 }}</div>
      <div class="value" style="color: var(--yellow)">{{ value4 }}</div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  label1: String,
  value1: [Number, String],
  label2: String,
  value2: [Number, String],
  label3: String,
  value3: [Number, String],
  label4: String,
  value4: [Number, String]
})
</script>

<style scoped>
.stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1rem;
  margin-bottom: 1.75rem;
}

.stat-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1.15rem 1.25rem;
  position: relative;
  overflow: hidden;
}

.stat-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
}

.stat-card:nth-child(1)::before {
  background: var(--accent);
}

.stat-card:nth-child(2)::before {
  background: var(--green);
}

.stat-card:nth-child(3)::before {
  background: var(--cyan);
}

.stat-card:nth-child(4)::before {
  background: var(--yellow);
}

.stat-card .label {
  font-size: 0.78rem;
  color: var(--muted);
  font-weight: 500;
}

.stat-card .value {
  font-size: 1.75rem;
  font-weight: 700;
  margin-top: 0.3rem;
  letter-spacing: -0.02em;
}
</style>
