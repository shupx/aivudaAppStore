import { createRouter, createWebHistory } from "vue-router";
import LoginView from "../views/LoginView.vue";
import StoreView from "../views/StoreView.vue";
import AppDetailView from "../views/AppDetailView.vue";
import MyAppsView from "../views/MyAppsView.vue";
import MyAppDetailView from "../views/MyAppDetailView.vue";
import NewAppView from "../views/NewAppView.vue";
import { session } from "../services/api";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", redirect: "/store" },
    { path: "/login", component: LoginView },
    { path: "/store", component: StoreView, meta: { requiresAuth: true } },
    { path: "/apps/:appId", component: AppDetailView, meta: { requiresAuth: true } },
    { path: "/me/apps", component: MyAppsView, meta: { requiresAuth: true } },
    { path: "/me/apps/:appId", component: MyAppDetailView, meta: { requiresAuth: true } },
    { path: "/me/new", component: NewAppView, meta: { requiresAuth: true } },
  ],
});

router.beforeEach((to) => {
  if (to.meta.requiresAuth && !session.token) return "/login";
  if (to.path === "/login" && session.token) return "/store";
  return true;
});

export default router;
