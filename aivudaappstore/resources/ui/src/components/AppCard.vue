<script setup>
import { useI18n } from "vue-i18n";

defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: "" },
  description: { type: String, default: "" },
  downloading: { type: Boolean, default: false },
  showDelete: { type: Boolean, default: false },
  deleting: { type: Boolean, default: false },
});

defineEmits(["click", "download", "delete"]);

const { t } = useI18n();
</script>

<template>
  <article class="app-card" @click="$emit('click')">
    <div class="app-head">
      <h3 :title="title">{{ title }}</h3>
    </div>
    <p class="sub">{{ subtitle }}</p>
    <p class="desc" :title="description || t('card.noDescription')">{{ description || t("card.noDescription") }}</p>
    <div class="download-btn-wrapper">
      <div v-if="showDelete" class="action-btn-wrap">
        <button class="app-delete" type="button" :disabled="deleting" @click.stop="$emit('delete')" :title="t('card.deleteApp')">
          <span v-if="deleting">...</span>
          <span v-else>🗑</span>
        </button>
        <div class="delete-tooltip">{{ t("card.deleteDanger") }}</div>
      </div>
      <div class="action-btn-wrap">
        <button class="app-download" type="button" :disabled="downloading" @click.stop="$emit('download')" :title="t('card.downloadApp')">
          <span v-if="downloading">...</span>
          <span v-else>⬇</span>
        </button>
        <div class="download-tooltip">{{ downloading ? t("card.downloading") : t("card.downloadPackage") }}</div>
      </div>
    </div>
  </article>
</template>
