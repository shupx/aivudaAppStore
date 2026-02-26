<script setup>
defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: "" },
  description: { type: String, default: "" },
  downloading: { type: Boolean, default: false },
});

defineEmits(["click", "download"]);
</script>

<template>
  <article class="app-card" @click="$emit('click')">
    <div class="app-head">
      <h3 :title="title">{{ title }}</h3>
    </div>
    <p class="sub">{{ subtitle }}</p>
    <p class="desc" :title="description || '暂无描述'">{{ description || "暂无描述" }}</p>
    <div class="download-btn-wrapper">
      <button class="app-download" type="button" :disabled="downloading" @click.stop="$emit('download')" title="下载应用">
        <span v-if="downloading">...</span>
        <span v-else>⬇</span>
      </button>
      <div class="download-tooltip">{{ downloading ? "下载中..." : "下载安装包" }}</div>
    </div>
  </article>
</template>
