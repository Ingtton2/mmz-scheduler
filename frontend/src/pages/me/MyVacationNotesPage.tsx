// 직원용 "휴가 일정 공유" — 개인 일정이 있는 달/기간을 미리 적어두고 서로 겹치지 않게 조율.
// 순수 참고용 (연차·사전휴무 신청과 무관). 입력은 정직원·점장만, 자동 저장(디바운스).
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  getMyVacationBoard,
  saveMyVacationNote,
  type DateRange,
  type VacationBoard,
  type VacationNote,
  type VacationNoteSave,
} from "../../api/vacationNotes";
import { MeApiError } from "../../api/meClient";
import VacationOverview from "../../components/vacation/VacationOverview";
import { useVacationTheme } from "../../components/vacation/useVacationTheme";
import {
  addDay,
  byYear,
  mergeRanges,
  mOf,
  pad,
  periodLabel,
  rangesIn,
  rText,
  rTextShort,
  yOf,
} from "../../components/vacation/vacationUtils";
import "../../components/vacation/vacation.css";
import MeNav from "./MeNav";

const SAVE_DELAY_MS = 600;
const MEMO_MAX = 60;

interface Mine {
  months: string[];
  ranges: DateRange[];
  noPlans: boolean;
  memo: string;
}

const EMPTY: Mine = { months: [], ranges: [], noPlans: false, memo: "" };

function toSave(m: Mine): VacationNoteSave {
  const months = [...m.months].sort();
  return {
    months,
    ranges: m.ranges.filter((r) => months.includes(r.start.slice(0, 7))),
    no_plans: m.noPlans && !months.length,
    memo: m.memo.trim().slice(0, MEMO_MAX),
  };
}

const hasContent = (s: VacationNoteSave) => s.months.length > 0 || s.no_plans || !!s.memo;

export default function MyVacationNotesPage() {
  useVacationTheme();
  const [board, setBoard] = useState<VacationBoard | null>(null);
  const [loadError, setLoadError] = useState("");
  const [mine, setMine] = useState<Mine>(EMPTY);
  const [status, setStatus] = useState("");

  // 자동 저장 상태 — 타이핑 중 서버 응답이 화면을 덮어쓰지 않도록 ref 로 관리.
  const dirty = useRef(false);
  const latest = useRef<Mine>(EMPTY);
  const timer = useRef<number | undefined>(undefined);
  const saving = useRef(false);
  const pending = useRef(false);

  const load = useCallback(async () => {
    try {
      const b = await getMyVacationBoard();
      setBoard(b);
      setLoadError("");
      if (!dirty.current) {
        const n = b.notes.find((x) => x.staff_id === b.my_staff_id);
        const m: Mine = n
          ? { months: n.months, ranges: n.ranges, noPlans: n.no_plans, memo: n.memo }
          : EMPTY;
        latest.current = m;
        setMine(m);
      }
    } catch (e) {
      setLoadError(e instanceof MeApiError ? e.message : "불러오지 못했어요. 새로고침해 주세요.");
    }
  }, []);

  useEffect(() => {
    load();
    // 다른 직원이 적은 내용은 앱으로 돌아올 때마다 새로 불러온다 (실시간 연결 대신).
    const onVisible = () => document.visibilityState === "visible" && load();
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      document.removeEventListener("visibilitychange", onVisible);
      window.clearTimeout(timer.current);
    };
  }, [load]);

  const save = useCallback(async () => {
    if (saving.current) {
      pending.current = true;
      return;
    }
    saving.current = true;
    try {
      await saveMyVacationNote(toSave(latest.current));
      setStatus("저장됐어요.");
    } catch (e) {
      setStatus(
        e instanceof MeApiError && e.status === 400
          ? e.message
          : "저장하지 못했어요. 잠시 후 다시 시도해 주세요.",
      );
    } finally {
      saving.current = false;
      if (pending.current) {
        pending.current = false;
        save();
      } else dirty.current = false;
    }
  }, []);

  function commit(next: Mine) {
    latest.current = next;
    setMine(next);
    dirty.current = true;
    setStatus("저장하는 중이에요…");
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(save, SAVE_DELAY_MS);
  }

  // 전체 현황에는 방금 고친 내 내용을 바로 반영해서 보여준다.
  const notes = useMemo<VacationNote[]>(() => {
    if (!board) return [];
    const others = board.notes.filter((n) => n.staff_id !== board.my_staff_id);
    if (!board.can_edit || board.my_staff_id == null) return others;
    const s = toSave(mine);
    if (!hasContent(s)) return others;
    const prev = board.notes.find((n) => n.staff_id === board.my_staff_id);
    return [
      ...others,
      {
        staff_id: board.my_staff_id,
        name: board.my_name ?? prev?.name ?? "",
        ...s,
        updated_at: prev?.updated_at ?? "",
      },
    ];
  }, [board, mine]);

  /* ---------- 날짜 선택 시트 ---------- */
  const sheetRef = useRef<HTMLDialogElement>(null);
  const [curK, setCurK] = useState<string | null>(null);
  const [draft, setDraft] = useState<DateRange[]>([]);
  const [anchor, setAnchor] = useState<string | null>(null);

  function openSheet(k: string) {
    setCurK(k);
    setDraft(rangesIn(mine.ranges, k).map((r) => ({ ...r })));
    setAnchor(null);
    sheetRef.current?.showModal();
  }
  function closeSheet() {
    sheetRef.current?.close();
  }
  function onDone() {
    if (!curK) return;
    const k = curK;
    commit({
      months: mine.months.includes(k) ? mine.months : [...mine.months, k],
      ranges: mergeRanges(mine.ranges.filter((r) => r.start.slice(0, 7) !== k).concat(draft)),
      noPlans: false,
      memo: mine.memo,
    });
    closeSheet();
  }
  function onRemove() {
    if (!curK) return;
    const k = curK;
    commit({
      ...mine,
      months: mine.months.filter((m) => m !== k),
      ranges: mine.ranges.filter((r) => r.start.slice(0, 7) !== k),
    });
    closeSheet();
  }
  function tapDay(ds: string) {
    if (!anchor) setAnchor(ds);
    else {
      const [a, b] = anchor < ds ? [anchor, ds] : [ds, anchor];
      setDraft(mergeRanges(draft.concat({ start: a, end: b })));
      setAnchor(null);
    }
  }

  if (loadError && !board) {
    return (
      <div className="vn">
        <MeNav current="휴가 일정 공유" />
        <p className="notice">{loadError}</p>
      </div>
    );
  }
  if (!board) {
    return (
      <div className="vn">
        <MeNav current="휴가 일정 공유" />
        <p className="notice">불러오는 중이에요…</p>
      </div>
    );
  }

  const counts: Record<string, number> = {};
  board.months.forEach((k) => (counts[k] = 0));
  notes.forEach((n) => n.months.forEach((k) => k in counts && counts[k]++));

  return (
    <div className="vn">
      <MeNav current="휴가 일정 공유" />
      <div className="intro">
        <h1>
          일정 있는 달이 있으면
          <br />
          알려주세요
        </h1>
        <p className="range">{periodLabel(board.months)}</p>
        <p>
          여행이나 개인 일정이 잡힌 달이 있다면 미리 적어주세요. 서로 겹치지 않게 조율할 때
          참고하고, 사전휴무 신청과는 별개예요.
        </p>
      </div>

      {board.can_edit ? (
        <div className="card">
          <h2>내 일정</h2>
          <p className="hint">
            달을 누르면 달력이 열려요. 날짜를 알면 기간을 표시하고, 아직 모르면 달만 선택해도
            괜찮아요.
          </p>
          <div role="group" aria-label="일정이 있는 달">
            {byYear(board.months).map(([y, ks]) => (
              <div key={y}>
                <div className="year">{y}년</div>
                <div className="mgrid">
                  {ks.map((k) => {
                    const sel = mine.months.includes(k);
                    const rs = rangesIn(mine.ranges, k);
                    const sub = sel
                      ? rs.length
                        ? rTextShort(rs[0]) + (rs.length > 1 ? ` 외 ${rs.length - 1}` : "")
                        : "날짜 미정"
                      : `${counts[k]}명`;
                    return (
                      <button
                        key={k}
                        type="button"
                        className="month"
                        aria-pressed={sel}
                        aria-haspopup="dialog"
                        aria-label={`${y}년 ${mOf(k)}월, ${counts[k]}명${sel ? ", 선택됨" : ""}, 달력 열기`}
                        onClick={() => openSheet(k)}
                      >
                        <b>{mOf(k)}월</b>
                        <span>{sub}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
          <button
            className="none"
            type="button"
            aria-pressed={mine.noPlans && !mine.months.length}
            onClick={() => {
              const noPlans = !mine.noPlans;
              commit(noPlans ? { ...mine, noPlans, months: [], ranges: [] } : { ...mine, noPlans });
            }}
          >
            특별한 일정은 없어요
          </button>
          <div className="field">
            <label htmlFor="vn-memo">
              메모 <span>(선택)</span>
            </label>
            <input
              className="memo"
              id="vn-memo"
              type="text"
              maxLength={MEMO_MAX}
              placeholder="예: 10월 둘째 주 가족 여행"
              autoComplete="off"
              value={mine.memo}
              onChange={(e) => commit({ ...mine, memo: e.target.value })}
            />
          </div>
          <div className="status" aria-live="polite">
            {status}
          </div>
        </div>
      ) : (
        <p className="notice">정직원·점장만 일정을 적을 수 있어요. 현황은 함께 볼 수 있어요.</p>
      )}

      <dialog
        className="sheet"
        ref={sheetRef}
        aria-labelledby="vn-sh-title"
        onClick={(e) => e.target === e.currentTarget && closeSheet()}
        onClose={() => setCurK(null)}
      >
        {curK && (
          <DaySheet
            k={curK}
            today={board.today}
            draft={draft}
            anchor={anchor}
            selected={mine.months.includes(curK)}
            others={notes.filter((n) => n.staff_id !== board.my_staff_id)}
            onTap={tapDay}
            onRemoveDraft={(i) => setDraft(draft.filter((_, j) => j !== i))}
            onClose={closeSheet}
            onRemove={onRemove}
            onDone={onDone}
          />
        )}
      </dialog>

      <VacationOverview months={board.months} notes={notes} myStaffId={board.my_staff_id} />
    </div>
  );
}

interface SheetProps {
  k: string;
  today: string;
  draft: DateRange[];
  anchor: string | null;
  selected: boolean;
  others: VacationNote[];
  onTap: (ds: string) => void;
  onRemoveDraft: (i: number) => void;
  onClose: () => void;
  onRemove: () => void;
  onDone: () => void;
}

function DaySheet({ k, today, draft, anchor, selected, others, onTap, onRemoveDraft, onClose, onRemove, onDone }: SheetProps) {
  const y = yOf(k);
  const m = mOf(k);
  const first = new Date(y, m - 1, 1).getDay();
  const days = new Date(y, m, 0).getDate();

  // 그날 일정 있는 "다른 직원 수"
  const oc: Record<string, number> = {};
  others.forEach((n) =>
    rangesIn(n.ranges, k).forEach((r) => {
      for (let d = r.start; d <= r.end; d = addDay(d, 1)) oc[d] = (oc[d] || 0) + 1;
    }),
  );

  return (
    <div className="sh-in">
      <div className="sh-head">
        <h3 id="vn-sh-title">
          {y}년 {m}월
        </h3>
        <button className="x" type="button" aria-label="닫기" onClick={onClose}>
          ✕
        </button>
      </div>
      <p className="sh-hint">
        시작일과 종료일을 차례로 눌러주세요. 하루만이면 같은 날을 두 번 누르면 돼요.
      </p>
      <div className="dow">
        {["일", "월", "화", "수", "목", "금", "토"].map((d) => (
          <span key={d}>{d}</span>
        ))}
      </div>
      <div className="cal">
        {Array.from({ length: first }, (_, i) => (
          <span key={`b${i}`} />
        ))}
        {Array.from({ length: days }, (_, i) => {
          const d = i + 1;
          const ds = `${k}-${pad(d)}`;
          const on = draft.some((r) => ds >= r.start && ds <= r.end);
          const cls = ["day", (first + d - 1) % 7 === 0 && "sun", on && "on", anchor === ds && "anchor"]
            .filter(Boolean)
            .join(" ");
          return (
            <button
              key={ds}
              type="button"
              className={cls}
              disabled={ds < today}
              aria-label={`${m}월 ${d}일${on ? ", 선택됨" : ""}${oc[ds] ? `, 다른 직원 ${oc[ds]}명` : ""}`}
              onClick={() => onTap(ds)}
            >
              <b>{d}</b>
              <small>{oc[ds] || ""}</small>
            </button>
          );
        })}
      </div>
      <p className="legend">날짜 아래 숫자는 그날 일정이 있는 다른 직원 수예요.</p>
      <div className="picked">
        {draft.length === 0 ? (
          <span className="empty-p">
            {anchor ? "종료일을 눌러주세요." : "선택한 날짜가 없어요. 날짜 없이 달만 선택할 수도 있어요."}
          </span>
        ) : (
          draft.map((r, i) => (
            <span key={r.start} className="pick">
              {m}월 {rText(r)}
              <button type="button" aria-label={`${rText(r)} 삭제`} onClick={() => onRemoveDraft(i)}>
                ✕
              </button>
            </span>
          ))
        )}
      </div>
      <div className="sh-actions">
        {selected && (
          <button className="btn ghost" type="button" onClick={onRemove}>
            선택 해제
          </button>
        )}
        <button className="btn primary" type="button" onClick={onDone}>
          {draft.length ? "완료" : "날짜 없이 이 달만 선택"}
        </button>
      </div>
    </div>
  );
}
