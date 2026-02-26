<script setup>
import { ref, onMounted, onBeforeUnmount } from "vue";
import { useRouter } from "vue-router";
import { logout, session } from "../services/api";

defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: "" },
  showBack: { type: Boolean, default: true },
});

const router = useRouter();
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
      <button v-if="showBack" class="icon-btn" @click="goBack" title="返回">←</button>
    </div>

    <div ref="accountWrap" class="account-wrap">
      <button class="icon-btn" @click="open = !open" title="账户">👤</button>
      <div v-if="open" class="account-menu">
        <div class="account-user">{{ session.user?.username }} ({{ session.user?.role }})</div>
        <button @click="go('/store')">全部应用</button>
        <button @click="go('/me/new')">+ 上传新应用</button>
        <button class="danger" @click="doLogout">退出登录</button>
      </div>
    </div>
  </header>
</template>
