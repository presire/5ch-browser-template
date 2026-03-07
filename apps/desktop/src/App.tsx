import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";

type MenuInfo = {
  topLevelKeys: number;
  normalizedSample: string;
};

type AuthEnvStatus = {
  beEmailSet: boolean;
  bePasswordSet: boolean;
  upliftEmailSet: boolean;
  upliftPasswordSet: boolean;
};

type LoginOutcome = {
  provider: "Be" | "Uplift" | "Donguri";
  success: boolean;
  status: number;
  location: string | null;
  cookieNames: string[];
  note: string;
};

type PostCookieReport = {
  targetUrl: string;
  cookieNames: string[];
};

export default function App() {
  const [status, setStatus] = useState("未取得");
  const [authStatus, setAuthStatus] = useState("未確認");
  const [loginProbe, setLoginProbe] = useState("未実行");
  const [postCookieProbe, setPostCookieProbe] = useState("未実行");

  const fetchMenu = async () => {
    setStatus("取得中...");
    try {
      const info = await invoke<MenuInfo>("fetch_bbsmenu_summary");
      setStatus(`ok keys=${info.topLevelKeys} sample=${info.normalizedSample}`);
    } catch (error) {
      setStatus(`error: ${String(error)}`);
    }
  };

  const checkAuthEnv = async () => {
    try {
      const s = await invoke<AuthEnvStatus>("check_auth_env_status");
      setAuthStatus(
        `BE(email:${s.beEmailSet}, pass:${s.bePasswordSet}) UPLIFT(email:${s.upliftEmailSet}, pass:${s.upliftPasswordSet})`
      );
    } catch (error) {
      setAuthStatus(`error: ${String(error)}`);
    }
  };

  const probeAuth = async () => {
    setLoginProbe("実行中...");
    try {
      const result = await invoke<LoginOutcome[]>("probe_auth_logins");
      const lines = result.map(
        (r) =>
          `${r.provider}: success=${r.success} status=${r.status} location=${r.location ?? "-"} cookies=${
            r.cookieNames.join(",") || "(none)"
          }`
      );
      setLoginProbe(lines.join("\n"));
    } catch (error) {
      setLoginProbe(`error: ${String(error)}`);
    }
  };

  const probePostCookieScope = async () => {
    setPostCookieProbe("実行中...");
    try {
      const r = await invoke<PostCookieReport>("probe_post_cookie_scope_simulation");
      setPostCookieProbe(`${r.targetUrl} -> ${r.cookieNames.join(",") || "(none)"}`);
    } catch (error) {
      setPostCookieProbe(`error: ${String(error)}`);
    }
  };

  return (
    <main className="app-root">
      <h1>5ch Browser (Phase 1 auth/fetch)</h1>
      <p>BE / UPLIFT / どんぐり認証と投稿Cookieスコープ基盤を実装中です。</p>
      <button onClick={fetchMenu}>bbsmenu.json 取得テスト</button>
      <pre>{status}</pre>
      <button onClick={checkAuthEnv}>BE/UPLIFT 設定確認</button>
      <pre>{authStatus}</pre>
      <button onClick={probeAuth}>認証ログイン観測（BE/UPLIFT/どんぐり）</button>
      <pre>{loginProbe}</pre>
      <button onClick={probePostCookieScope}>投稿先Cookieスコープ確認</button>
      <pre>{postCookieProbe}</pre>
    </main>
  );
}
