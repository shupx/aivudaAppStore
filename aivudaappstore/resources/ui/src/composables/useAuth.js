import { reactive } from "vue";
import { login, register, session } from "../services/api";

export function useAuth(t) {
  const form = reactive({ username: "", password: "" });
  const status = reactive({ text: t("login.notLoggedIn"), loading: false, type: "info" });

  async function submitAuth(mode, { onSuccess } = {}) {
    status.loading = true;
    try {
      const action = mode === "register" ? register : login;
      const data = await action(form.username, form.password);
      localStorage.setItem("appstore_last_username", form.username);
      status.type = "success";
      status.text = mode === "register"
        ? t("login.registerSuccess", { username: data.user.username })
        : t("login.success", { username: data.user.username });
      if (onSuccess) onSuccess(data);
      return data;
    } catch (err) {
      status.type = "error";
      status.text = String(err);
      return null;
    } finally {
      status.loading = false;
    }
  }

  return {
    session,
    form,
    status,
    loginWithForm(options) {
      return submitAuth("login", options);
    },
    registerWithForm(options) {
      return submitAuth("register", options);
    },
  };
}
