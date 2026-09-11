// 직원 셀프서비스 홈 (스펙 9-4). 로그인 후 첫 화면.
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getMe, type MeInfo } from "../../api/me";
import { LABEL } from "../../labels";
import MeNav from "./MeNav";

const MENU = [
  { key: "schedule", label: "내 스케줄 조회", to: "/me/schedule" },
  { key: "leave", label: "연차 신청", to: "/me/leave" },
  { key: "dayoff", label: "사전 휴무 신청", to: "/me/dayoff" },
  { key: "pin", label: "PIN 변경", to: "/me/change-pin" },
];

export default function MyHome() {
  const [me, setMe] = useState<MeInfo | null>(null);

  useEffect(() => {
    getMe()
      .then(setMe)
      .catch(() => setMe(null));
  }, []);

  const isPartTime = me?.employment_type === "part_time";

  return (
    <div>
      <MeNav current="내 화면" />
      <h1 className="mb-1 text-xl font-bold">
        안녕하세요{me ? `, ${me.name}님` : ""}
      </h1>
      <p className="mb-6 text-sm text-gray-500">
        {me && `${LABEL.role[me.role] ?? me.role} · ${LABEL.position[me.position] ?? me.position}`}
      </p>

      <ul className="grid gap-3 sm:grid-cols-2">
        {MENU.map((m) => {
          const disabled = isPartTime && (m.key === "leave" || m.key === "dayoff");
          return (
            <li key={m.key}>
              {disabled ? (
                <div className="rounded-lg border bg-white p-4 opacity-50">
                  <div className="font-semibold">{m.label}</div>
                  <div className="mt-1 text-xs text-gray-400">
                    파트타임은 신청 대상이 아니에요
                  </div>
                </div>
              ) : (
                <Link
                  to={m.to}
                  className="block rounded-lg border bg-white p-4 transition hover:border-gray-400 hover:shadow-sm"
                >
                  <div className="font-semibold">{m.label}</div>
                  <div className="mt-1 text-xs text-gray-400">바로 가기 →</div>
                </Link>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
