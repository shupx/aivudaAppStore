<script setup>
defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: "" },
  description: { type: String, default: "" },
});

defineEmits(["click"]);
</script>

<template>
  <article class="app-card" @click="$emit('click')">
    <div class="app-head">
      <h3 :title="title">{{ title }}</h3>
    </div>
    <p class="sub">{{ subtitle }}</p>
    <p class="desc" :title="description || '暂无描述'">{{ description || "暂无描述" }}</p>
  </article>
</template>
