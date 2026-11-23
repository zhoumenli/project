<template>
  <div class="pager" v-if="total > 0">
    <span class="pg-total">共 {{ total }} 条 / {{ pages }} 页</span>
    <button class="pg-btn" :disabled="page <= 1" @click="go(page - 1)">‹ 上一页</button>
    <button v-for="p in pageList" :key="p.k" class="pg-num" :class="{ active: p.n === page, gap: p.n === 0 }"
      :disabled="p.n === 0" @click="go(p.n)" :title="p.n === 0 ? '' : `第 ${p.n} 页`">{{ p.n === 0 ? '…' : p.n }}</button>
    <button class="pg-btn" :disabled="page >= pages" @click="go(page + 1)">下一页 ›</button>
    <select class="pg-size" :value="size" @change="$emit('update:size', Number($event.target.value))" title="每页条数">
      <option :value="30">30 条/页</option>
      <option :value="50">50 条/页</option>
      <option :value="100">100 条/页</option>
    </select>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  total: { type: Number, default: 0 },
  page: { type: Number, default: 1 },   // v-model:page
  size: { type: Number, default: 30 },  // v-model:size
})
const emit = defineEmits(['update:page', 'update:size'])

const pages = computed(() => Math.max(1, Math.ceil(props.total / props.size)))

// 页码窗口：首尾常驻，当前页 ±1，超出折叠为省略号
const pageList = computed(() => {
  const n = pages.value, cur = props.page, out = []
  const push = v => out.push({ n: v, k: 'p' + v })
  if (n <= 8) { for (let i = 1; i <= n; i++) push(i); return out }
  push(1)
  const lo = Math.max(2, cur - 1), hi = Math.min(n - 1, cur + 1)
  if (lo > 2) out.push({ n: 0, k: 'g1' })
  for (let i = lo; i <= hi; i++) push(i)
  if (hi < n - 1) out.push({ n: 0, k: 'g2' })
  push(n)
  return out
})

function go(p) {
  if (p < 1 || p > pages.value || p === props.page) return
  emit('update:page', p)
}
</script>

<style scoped>
.pager { display: flex; align-items: center; gap: 6px; padding: 12px 2px 0; flex-wrap: wrap; }
.pg-total { font-size: 12px; color: var(--muted, #8a90a0); margin-right: 6px; }
.pg-btn, .pg-num { border: 1px solid var(--border, var(--border)); background: var(--panel); border-radius: 7px; padding: 4px 10px; font-size: 12px; cursor: pointer; color: var(--text, #2c2c2a); }
.pg-btn:disabled { opacity: .4; cursor: not-allowed; }
.pg-num.active { background: var(--primary, #5b6bf5); border-color: var(--primary, #5b6bf5); color: #fff; }
.pg-num.gap { border: none; background: none; cursor: default; }
.pg-size { border: 1px solid var(--border, var(--border)); border-radius: 7px; padding: 4px 6px; font-size: 12px; margin-left: 4px; }
</style>
