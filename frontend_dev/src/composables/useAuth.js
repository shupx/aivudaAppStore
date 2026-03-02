import { reactive } from "vue";
import { login, session, setBaseUrl } from "../services/api";

export function useAuth(t) {
  const form = reactive({ username: "admin", password: "admin123" });
  const status = reactive({ text: t("login.notLoggedIn") });

  async function loginWithForm({ onSuccess } = {}) {
    try {
      setBaseUrl(session.baseUrl);
      const data = await login(form.username, form.password);
      status.text = t("login.success", { username: data.user.username });
      if (onSuccess) onSuccess(data);
      return data;
    } catch (err) {
      status.text = String(err);
      return null;
    }
  }

  return {
    session,
    form,
    status,
    loginWithForm,
  };
}
