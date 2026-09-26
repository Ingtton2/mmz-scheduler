// 휴가 일정 공유 "전체 현황" 카드 — 직원 화면과 관리자 화면이 같이 쓴다.
// 월별 히트맵(그 달에 일정 있다고 한 인원) + 달을 누르면 그 달 직원들의 기간/메모.
import { useState } from "react";
import type { VacationNote } from "../../api/vacationNotes";
import { byYear, mOf, rangesIn, rText, yOf } from "./vacationUtils";

interface Props {
  months: string[];
  notes: VacationNote[];
  myStaffId?: number | null;
}

export default function VacationOverview({ months, notes, myStaffId }: Props) {
  const [open, setOpen] = useState<string | null>(null);

  const counts: Record<string, number> = {};
  months.forEach((k) => (counts[k] = 0));
  notes.forEach((n) => n.months.forEach((k) => k in counts && counts[k]++));
  const max = Math.max(1, ...Object.values(counts));

  const people = open
    ? notes
        .filter((n) => n.months.includes(open))
        .sort((a, b) =>
          (a.staff_id === myStaffId) !== (b.staff_id === myStaffId)
            ? a.staff_id === myStaffId
              ? -1
              : 1
            : a.name.localeCompare(b.name, "ko"),
        )
    : [];

  return (
    <div className="card">
      <h2>전체 현황</h2>
      <p className="hint">달을 누르면 그 달에 누가 언제 일정이 있는지 보여요.</p>
      {byYear(months).map(([y, ks]) => (
        <div key={y}>
          <div className="year">{y}년</div>
          <div className="months">
            {ks.map((k) => (
              <button
                key={k}
                type="button"
                className="mcell"
                aria-pressed={open === k}
                aria-label={`${y}년 ${mOf(k)}월, ${counts[k]}명`}
                onClick={() => setOpen(open === k ? null : k)}
              >
                <span
                  className="fill"
                  style={{ "--h": `${(counts[k] / max) * 100}%` } as React.CSSProperties}
                />
                <small>{mOf(k)}월</small>
                <b>{counts[k]}</b>
              </button>
            ))}
          </div>
        </div>
      ))}

      {open && (
        <div className="detail">
          <h3 className="sub-h">
            {yOf(open)}년 {mOf(open)}월
          </h3>
          {people.length === 0 ? (
            <p className="empty">이 달에 일정 있다고 한 사람이 없어요.</p>
          ) : (
            <ul className="people">
              {people.map((n) => {
                const rs = rangesIn(n.ranges, open);
                const isMe = n.staff_id === myStaffId;
                return (
                  <li key={n.staff_id} className="person">
                    <span className="avatar" aria-hidden="true">
                      {n.name.slice(0, 1)}
                    </span>
                    <div className="body">
                      <div className="name">
                        {n.name}
                        {isMe && <em>나</em>}
                      </div>
                      <div className="chips">
                        {rs.length ? (
                          rs.map((r) => (
                            <span key={r.start} className="chip">
                              {mOf(open)}월 {rText(r)}
                            </span>
                          ))
                        ) : (
                          <span className="chip quiet">날짜 미정</span>
                        )}
                      </div>
                      {n.memo && <div className="note">{n.memo}</div>}
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
