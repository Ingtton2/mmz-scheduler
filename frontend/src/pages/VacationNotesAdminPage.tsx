// 관리자용 "휴가 일정 공유" — 직원들이 적은 개인 일정을 조회만 한다 (승인/확정 없음).
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getVacationBoard, type VacationBoard } from "../api/vacationNotes";
import VacationOverview from "../components/vacation/VacationOverview";
import { useVacationTheme } from "../components/vacation/useVacationTheme";
import { periodLabel } from "../components/vacation/vacationUtils";
import "../components/vacation/vacation.css";

export default function VacationNotesAdminPage() {
  useVacationTheme();
  const [board, setBoard] = useState<VacationBoard | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getVacationBoard()
      .then(setBoard)
      .catch((e) => setError(e instanceof Error ? e.message : "불러오지 못했어요."));
  }, []);

  return (
    <div className="vn">
      <div className="mb-4 text-sm">
        <Link to="/admin" className="text-gray-500 hover:underline">
          ← 관리자 홈
        </Link>
      </div>
      <div className="intro">
        <h1>휴가 일정 공유</h1>
        {board && <p className="range">{periodLabel(board.months)}</p>}
        <p>
          직원들이 미리 적어둔 개인 일정이에요. 참고용이라 사전휴무 신청·연차와는 별개예요.
        </p>
      </div>
      {error && <p className="notice">{error}</p>}
      {board && <VacationOverview months={board.months} notes={board.notes} />}
    </div>
  );
}
