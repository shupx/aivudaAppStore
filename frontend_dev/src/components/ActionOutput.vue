<script setup>
import { useI18n } from "vue-i18n";

defineProps({
  output: { type: Object, default: () => ({ text: "", isError: false }) },
});

const { t } = useI18n();
</script>

<template>
  <section class="card output-box">
    <h2>{{ t("output.title") }}</h2>
    <pre :class="{ 'output-error': output.isError }">{{ output.text }}</pre>
  </section>
</template>

<style scoped>
.output-error {
  color: #e53935;
}
</style>
