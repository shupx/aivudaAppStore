<script setup>
import { onMounted } from "vue";
import { useI18n } from "vue-i18n";
import { useAppStoreVersion } from "../composables/useAppStoreVersion";

const { t } = useI18n();
const { version, loadVersion } = useAppStoreVersion();

onMounted(() => {
  loadVersion();
});
</script>

<template>
  <div
    class="pointer-events-none fixed bottom-4 right-4 z-50 rounded-full border border-zinc-200/80 bg-white/88 px-4 py-2 text-xs font-medium text-zinc-600 shadow-lg shadow-zinc-300/30 backdrop-blur-md dark:border-zinc-700/70 dark:bg-zinc-900/80 dark:text-zinc-300 dark:shadow-black/30"
  >
    {{ t("app.versionBadge", { version }) }}
  </div>
</template>
