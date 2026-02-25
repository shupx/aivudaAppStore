<script setup>
defineProps({ output: { type: String, default: "" } });
</script>

<template>
  <section class="card output-box">
    <h2>输出</h2>
    <pre>{{ output }}</pre>
  </section>
</template>
