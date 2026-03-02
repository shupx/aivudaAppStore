<script setup>
import { ref, onMounted, onBeforeUnmount } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { logout, session } from "../services/api";
import shoppingBagIcon from "../assets/icons/shopping-bag.svg";
import { setLocale } from "../i18n";

defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: "" },
  showBack: { type: Boolean, default: true },
});

const router = useRouter();
const { t, locale } = useI18n();
const open = ref(false);
const accountWrap = ref(null);

function go(path) {
  open.value = false;
  router.push(path);
}

function goBack() {
  open.value = false;
  if (window.history.length > 1) {
    router.back();
    return;
  }
  router.push("/store");
}

function doLogout() {
  open.value = false;
  logout();
  router.push("/login");
}

async function changeLocale(locale) {
  await setLocale(locale);
}

function closeMenu() {
  open.value = false;
}

function handleClickOutside(event) {
  if (accountWrap.value && !accountWrap.value.contains(event.target)) {
    open.value = false;
  }
}

onMounted(() => {
  document.addEventListener("click", handleClickOutside);
});

onBeforeUnmount(() => {
  document.removeEventListener("click", handleClickOutside);
});
</script>

<template>
  <header class="topbar card">
    <div>
      <h1>{{ title }}</h1>
      <p>{{ subtitle }}</p>
    </div>

    <div class="topbar-actions">
      <button v-if="showBack" class="icon-btn" @click="goBack" :title="t('common.back')">←</button>
      <div class="lang-switch" :aria-label="t('common.language')">
        <span class="lang-label">{{ t("common.language") }}</span>
        <button
          type="button"
          class="lang-btn"
          :class="{ active: locale === 'zh-CN' }"
          @click="changeLocale('zh-CN')"
        >
          {{ t("topbar.zhCN") }}
        </button>
        <button
          type="button"
          class="lang-btn"
          :class="{ active: locale === 'en-US' }"
          @click="changeLocale('en-US')"
        >
          {{ t("topbar.enUS") }}
        </button>
      </div>
    </div>

    <button class="icon-btn store-bag-btn" @click="go('/store')" :title="t('common.allApps')">
      <img :src="shoppingBagIcon" :alt="t('common.allApps')" width="22" height="22" />
    </button>

    <div ref="accountWrap" class="account-wrap">
      <button class="icon-btn" @click="open = !open" :title="t('common.account')">👤</button>
      <div v-if="open" class="account-menu">
        <div class="account-user">{{ session.user?.username }} ({{ session.user?.role }})</div>
        <button @click="go('/me/new')">{{ t('common.uploadNewApp') }}</button>
        <button class="danger" @click="doLogout">{{ t('common.logout') }}</button>
      </div>
    </div>
  </header>
</template>
