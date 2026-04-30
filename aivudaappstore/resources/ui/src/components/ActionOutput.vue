<script setup>
import { useI18n } from "vue-i18n";
import { Terminal } from "lucide-vue-next";

defineProps({
  output: { type: Object, default: () => ({ text: "", isError: false }) },
});

const { t } = useI18n();
</script>

<template>
  <section class="bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-3xl p-5 shadow-inner">
    <h2 class="text-sm font-bold text-zinc-500 dark:text-zinc-400 m-0 mb-3 flex items-center gap-2 uppercase tracking-wider">
      <Terminal class="w-4 h-4" /> {{ t("output.title") }}
    </h2>
    <div class="bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-xl p-4 max-h-[340px] overflow-auto shadow-sm">
      <pre 
        class="m-0 font-mono text-sm whitespace-pre-wrap break-words"
        :class="output.isError ? 'text-red-500 dark:text-red-400' : 'text-zinc-700 dark:text-zinc-300'"
      >{{ output.text }}</pre>
    </div>
  </section>
</template>
