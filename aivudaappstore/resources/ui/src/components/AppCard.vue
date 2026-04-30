<script setup>
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import { Download, Trash2, Loader2 } from "lucide-vue-next";
import { formatDate } from "../utils/format";

const props = defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: "" },
  description: { type: String, default: "" },
  createdAt: { type: Number, default: 0 },
  updatedAt: { type: Number, default: 0 },
  downloading: { type: Boolean, default: false },
  showDelete: { type: Boolean, default: false },
  deleting: { type: Boolean, default: false },
});

defineEmits(["click", "download", "delete"]);

const { t } = useI18n();
const createdAtText = computed(() => formatDate(props.createdAt));
const updatedAtText = computed(() => formatDate(props.updatedAt));
</script>

<template>
  <article 
    class="relative border border-zinc-200 dark:border-zinc-700/60 bg-white/80 dark:bg-zinc-800/40 backdrop-blur-md rounded-2xl p-5 pb-16 cursor-pointer transition-all duration-300 hover:border-emerald-500/60 dark:hover:border-emerald-500/60 hover:bg-zinc-50 dark:hover:bg-zinc-800/60 hover:-translate-y-1 shadow-lg shadow-zinc-200 dark:shadow-black/40 hover:shadow-emerald-500/10 group"
    @click="$emit('click')"
  >
    <div class="flex justify-between items-center gap-2">
      <h3 class="m-0 text-lg font-bold text-zinc-900 dark:text-zinc-100 overflow-hidden text-ellipsis whitespace-nowrap" :title="title">
        {{ title }}
      </h3>
    </div>
    
    <p class="text-sm text-zinc-500 dark:text-zinc-400 mt-1 mb-3">{{ subtitle }}</p>
    
    <p class="text-zinc-700 dark:text-zinc-300 text-sm m-0 overflow-hidden line-clamp-2" :title="description || t('card.noDescription')">
      {{ description || t("card.noDescription") }}
    </p>

    <div class="mt-4 flex flex-col gap-1 text-xs text-zinc-500 dark:text-zinc-400">
      <span>{{ t("card.createdAt") }} {{ createdAtText }}</span>
      <span>{{ t("card.updatedAt") }} {{ updatedAtText }}</span>
    </div>

    <div class="absolute right-4 bottom-4 flex items-center gap-2">
      <div v-if="showDelete" class="relative group/delete">
        <button 
          class="w-8 h-8 rounded-lg flex items-center justify-center bg-red-500/10 border border-red-500/30 text-red-600 dark:text-red-500 transition-all hover:bg-red-500 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed"
          type="button" 
          :disabled="deleting" 
          @click.stop="$emit('delete')" 
          :title="t('card.deleteApp')"
        >
          <Loader2 v-if="deleting" class="w-4 h-4 animate-spin" />
          <Trash2 v-else class="w-4 h-4" />
        </button>
        <div class="absolute bottom-full right-0 mb-2 whitespace-nowrap bg-zinc-900 dark:bg-zinc-950 text-red-400 border border-red-500/30 text-xs px-2 py-1 rounded opacity-0 group-hover/delete:opacity-100 pointer-events-none transition-opacity">
          {{ t("card.deleteDanger") }}
        </div>
      </div>
      
      <div class="relative group/download">
        <button 
          class="w-8 h-8 rounded-lg flex items-center justify-center bg-emerald-500/10 border border-emerald-500/30 text-emerald-600 dark:text-emerald-400 transition-all hover:bg-emerald-500 hover:text-zinc-950 disabled:opacity-50 disabled:cursor-not-allowed"
          type="button" 
          :disabled="downloading" 
          @click.stop="$emit('download')" 
          :title="t('card.downloadApp')"
        >
          <Loader2 v-if="downloading" class="w-4 h-4 animate-spin" />
          <Download v-else class="w-4 h-4" />
        </button>
        <div class="absolute bottom-full right-0 mb-2 whitespace-nowrap bg-zinc-900 dark:bg-zinc-950 text-emerald-400 border border-emerald-500/30 text-xs px-2 py-1 rounded opacity-0 group-hover/download:opacity-100 pointer-events-none transition-opacity">
          {{ downloading ? t("card.downloading") : t("card.downloadPackage") }}
        </div>
      </div>
    </div>
  </article>
</template>
