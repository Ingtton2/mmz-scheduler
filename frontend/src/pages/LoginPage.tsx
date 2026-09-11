// 관리자 로그인 화면 (스펙 9 간이 버전). /admin/... 은 여기를 통과해야 접근 가능.
import { useState } from "react";
import type { FormEvent } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { login } from "../api/auth";
import { ApiError, setToken } from "../api/client";
import logo from "../assets/logo.png";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const { token } = await login(username, password);
      setToken(token);
      const from = (location.state as { from?: string } | null)?.from || "/admin";
      navigate(from, { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "로그인에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto mt-24 max-w-sm rounded-lg border bg-white p-6 shadow-sm">
      <img src={logo} alt="memeal.zip" className="mx-auto mb-4 h-16 w-16 rounded" />
      <h1 className="mb-1 text-center text-lg font-bold">관리자 로그인</h1>
      <p className="mb-5 text-center text-sm text-gray-500">
        사장님만 이 화면 뒤 관리자 기능을 사용할 수 있어요.
      </p>
      <form onSubmit={onSubmit} className="space-y-3">
        <div>
          <label className="mb-1 block text-sm text-gray-600">아이디</label>
          <input
            className="w-full rounded border px-3 py-2"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoFocus
            autoComplete="username"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm text-gray-600">비밀번호</label>
          <input
            type="password"
            className="w-full rounded border px-3 py-2"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
          />
        </div>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          disabled={loading}
          className="w-full rounded bg-gray-900 py-2 text-white disabled:opacity-50"
        >
          {loading ? "로그인 중..." : "로그인"}
        </button>
      </form>
    </div>
  );
}
