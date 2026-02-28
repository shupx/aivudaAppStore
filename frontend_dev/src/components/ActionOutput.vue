<script setup>
defineProps({
  output: { type: Object, default: () => ({ text: "", isError: false }) },
});
</script>

<template>
  <section class="card output-box">
    <h2>输出</h2>
    <pre :class="{ 'output-error': output.isError }">{{ output.text }}</pre>
  </section>
</template>

<style scoped>
.output-error {
  color: #e53935;
}
</style>
