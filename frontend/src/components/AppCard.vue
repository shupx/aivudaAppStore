<script setup>
defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: "" },
  description: { type: String, default: "" },
  tag: { type: String, default: "" },
});

defineEmits(["click"]);
</script>

<template>
  <article class="app-card" @click="$emit('click')">
    <div class="app-head">
      <h3>{{ title }}</h3>
      <span v-if="tag" class="chip">{{ tag }}</span>
    </div>
    <p class="sub">{{ subtitle }}</p>
    <p class="desc">{{ description || '暂无描述' }}</p>
  </article>
</template>
