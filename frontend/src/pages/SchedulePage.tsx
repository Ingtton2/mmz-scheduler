// 자동배치 + 수동 수정 + 공유 화면 (스펙 5, 6.1, 7).
//  - "자동배치 실행" -> OR-Tools 엔진이 근무표 계산·저장·표시
//  - 표의 셀을 클릭해서 근무 코드를 바꾸고 "수정 저장" -> 반영
//  - "직원에게 공개" -> 상태를 "confirmed"로 바꿔 로그인한 직원이 조회 가능해짐
//  - 근무 코드: 홀 FO/FC · 주방 BO/BM/BC · 파트타임 풀오마
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import html2canvas from "html2canvas";
import { getHolidays } from "../api/holiday";
import {
  getRotation,
  saveRotation,
  SLOT_LABEL,
  type RotationItem,
  type RotationSlot,
} from "../api/kitchenRotation";
import {
  EDIT_CODES,
  editScheduleEntries,
  getLeavePlan,
  getSavedSchedule,
  runAutoSchedule,
  shareSchedule,
  type LeaveDays,
  type LeavePlanRow,
  type ScheduleResult,
  type ScheduleRow,
} from "../api/schedule";
import { LABEL } from "../labels";

const WD_CHAR = ["일", "월", "화", "수", "목", "금", "토"];

function parseWd(dateStr: string): number {
  const [y, m, d] = dateStr.split("-").map(Number);
  return new Date(y, m - 1, d).getDay(); // 0=일 ~ 6=토
}

function fmtPublishedAt(iso: string): string {
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

// 저장된 코드 -> 화면 표시(뱃지). 근무 코드마다 서로 다른 색 (memeal.zip 디자인 시스템).
export const CELL: Record<string, { short: string; cls: string }> = {
  FO: { short: "FO", cls: "bg-fo text-fo-ink" },
  FC: { short: "FC", cls: "bg-fc text-fc-ink" },
  BO: { short: "BO", cls: "bg-bo text-bo-ink" },
  BM: { short: "BM", cls: "bg-bm text-bm-ink" },
  BC: { short: "BC", cls: "bg-bc text-bc-ink" },
  풀오마: { short: "풀", cls: "bg-full text-full-ink" },
  사휴: { short: "사", cls: "bg-dayoff text-dayoff-ink" },
  "D/O": { short: "휴", cls: "bg-off text-off-ink" },
  연차: { short: "연", cls: "bg-leave text-leave-ink" },
  // 구버전 저장분 호환
  O: { short: "O", cls: "bg-fo text-fo-ink" },
  M: { short: "M", cls: "bg-bm text-bm-ink" },
  C: { short: "C", cls: "bg-fc text-fc-ink" },
  근무: { short: "근", cls: "bg-fo text-fo-ink" },
};

const now = new Date();
const NEXT_MONTH = now.getMonth() + 2 > 12 ? 1 : now.getMonth() + 2;
const NEXT_MONTH_YEAR =
  now.getMonth() + 2 > 12 ? now.getFullYear() + 1 : now.getFullYear();

// 시점(당월 기준) 제한 — 서버가 최종 판단하지만, 화면에서도 미리 막아서
// 헷갈리지 않게 한다. ym 을 정수 하나로 비교(연*12+월)해서 대소비교를 간단히 함.
const ymValue = (y: number, m: number) => y * 12 + m;
const CURRENT_YM = ymValue(now.getFullYear(), now.getMonth() + 1);
// 자동배치(전체 재계산): 당월 포함 과거는 금지, 다음 달부터만 가능.
const isAutoScheduleBlocked = (y: number, m: number) => ymValue(y, m) <= CURRENT_YM;
// 수동 수정(칸 단위): 과거(당월 이전)만 금지, 당월부터는 계속 가능.
const isManualEditBlocked = (y: number, m: number) => ymValue(y, m) < CURRENT_YM;

const cellKey = (staffId: number, date: string) => `${staffId}|${date}`;

// 일자별 통계(총근무/주방/홀 인원)용 코드 분류. FO/FC=홀, BO/BM/BC=주방, 풀오마=홀
// (풀타임 홀 커버). O/C/M 은 구버전 저장분 호환.
const HALL_CODES = new Set(["FO", "FC", "풀오마", "O", "C"]);
const KITCHEN_CODES = new Set(["BO", "BM", "BC", "M"]);

interface DayStat {
  total: number;
  hall: number;
  kitchen: number;
}

function computeDayStats(
  result: ScheduleResult,
  edits: Record<string, string>,
): Record<string, DayStat> {
  const stats: Record<string, DayStat> = {};
  for (const d of result.days) {
    let hall = 0;
    let kitchen = 0;
    for (const row of result.rows) {
      const code = edits[cellKey(row.staff_id, d)] ?? row.cells[d] ?? "";
      if (HALL_CODES.has(code)) hall++;
      else if (KITCHEN_CODES.has(code)) kitchen++;
    }
    stats[d] = { hall, kitchen, total: hall + kitchen };
  }
  return stats;
}

export default function SchedulePage() {
  const [year, setYear] = useState(NEXT_MONTH_YEAR);
  const [month, setMonth] = useState(NEXT_MONTH);
  const [result, setResult] = useState<ScheduleResult | null>(null);
  const [running, setRunning] = useState(false);
  // 직원별 "이번 달 연차 사용 개수" 입력 (자동배치가 날짜를 랜덤으로 골라 넣음)
  const [leavePlan, setLeavePlan] = useState<LeavePlanRow[]>([]);
  const [leaveInputs, setLeaveInputs] = useState<Record<number, string>>({});
  // 이번 달 주방 로테이션(전월 기준 자동 계산). 사장님이 실행 전에 확인하고 바꿀 수 있음.
  const [rotation, setRotation] = useState<RotationItem[]>([]);
  const [rotationSaved, setRotationSaved] = useState(false);
  const [rotationEdited, setRotationEdited] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // 공휴일(대체공휴일 포함) — 관리자가 등록한 날짜. 표시 전용, 자동배치엔 영향 없음.
  const [holidays, setHolidays] = useState<Record<string, string>>({});

  // 수동 수정
  const [edits, setEdits] = useState<Record<string, string>>({});
  const [editingCell, setEditingCell] = useState<string | null>(null);
  const [savingEdits, setSavingEdits] = useState(false);

  // 공유 (직원에게 공개)
  const [sharing, setSharing] = useState(false);

  // 이미지 다운로드 (확정된 스케줄만)
  const gridRef = useRef<HTMLDivElement>(null);
  const [downloading, setDownloading] = useState(false);

  const dirtyCount = Object.keys(edits).length;
  const dayStats = result ? computeDayStats(result, edits) : {};

  function resetTransient() {
    setEdits({});
    setEditingCell(null);
  }

  async function loadSaved(y: number, m: number) {
    setLoading(true);
    resetTransient();
    try {
      setResult(await getSavedSchedule(y, m));
      setError("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadSaved(year, month);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    getHolidays()
      .then((list) => {
        const map: Record<string, string> = {};
        for (const h of list) map[h.date] = h.name;
        setHolidays(map);
      })
      .catch(() => {
        /* 표시 전용 정보라 실패해도 화면을 막지 않음 */
      });
  }, []);

  useEffect(() => {
    let cancelled = false;
    getLeavePlan(year, month)
      .then((rows) => {
        if (cancelled) return;
        setLeavePlan(rows);
        const next: Record<number, string> = {};
        for (const r of rows) next[r.staff_id] = r.saved_days > 0 ? String(r.saved_days) : "";
        setLeaveInputs(next);
      })
      .catch(() => {
        if (!cancelled) setLeavePlan([]);
      });
    return () => {
      cancelled = true;
    };
  }, [year, month]);

  useEffect(() => {
    let cancelled = false;
    getRotation(year, month)
      .then((p) => {
        if (cancelled) return;
        setRotation(p.items);
        setRotationSaved(p.saved);
        setRotationEdited(false);
      })
      .catch(() => {
        if (!cancelled) setRotation([]);
      });
    return () => {
      cancelled = true;
    };
  }, [year, month]);

  function setRotationSlot(staffId: number, slot: RotationSlot) {
    setRotation((prev) => prev.map((r) => (r.staff_id === staffId ? { ...r, position: slot } : r)));
    setRotationEdited(true);
  }
  // 오픈/미들/마감을 한 명씩 맡아야 함 (겹치면 로테이션이 어긋남)
  const rotationDuplicate =
    rotation.length > 0 && new Set(rotation.map((r) => r.position)).size !== rotation.length;

  // 입력값 -> 개수. 비었으면 0, 음수/소수/잔여 초과면 오류 메시지.
  function leaveInputError(r: LeavePlanRow): string {
    const raw = (leaveInputs[r.staff_id] ?? "").trim();
    if (raw === "") return "";
    const n = Number(raw);
    if (!Number.isInteger(n) || n < 0) return "0 이상 정수";
    if (n > r.max_days) return "잔여 초과";
    return "";
  }
  const leaveHasError = leavePlan.some((r) => leaveInputError(r) !== "");

  async function handleRun() {
    const leaveDays: LeaveDays = {};
    for (const r of leavePlan) {
      const n = Number((leaveInputs[r.staff_id] ?? "").trim() || "0");
      if (n > 0) leaveDays[r.staff_id] = n;
    }
    setRunning(true);
    resetTransient();
    try {
      if (rotationEdited && rotation.length > 0) {
        // 사장님이 고친 로테이션을 먼저 저장 — 자동배치가 이 값을 우선 배정 기준으로 씀
        await saveRotation(
          year,
          month,
          rotation.map((r) => ({ staff_id: r.staff_id, position: r.position })),
        );
      }
      setResult(await runAutoSchedule(year, month, leaveDays));
      getRotation(year, month)
        .then((p) => {
          setRotation(p.items);
          setRotationSaved(p.saved);
          setRotationEdited(false);
        })
        .catch(() => {});
      // 실행하면 사용연차가 차감되므로 잔여/저장 개수를 다시 불러온다
      getLeavePlan(year, month).then(setLeavePlan).catch(() => {});
      setError("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setRunning(false);
    }
  }

  function onPeriodChange(y: number, m: number) {
    setYear(y);
    setMonth(m);
    setResult(null);
    loadSaved(y, m);
  }

  function pickCode(key: string, code: string, original: string) {
    setEditingCell(null);
    setEdits((prev) => {
      const next = { ...prev };
      if (code === original) delete next[key];
      else next[key] = code;
      return next;
    });
  }

  async function saveEdits() {
    if (!result || dirtyCount === 0) return;
    setSavingEdits(true);
    try {
      const changes = Object.entries(edits).map(([k, work_code]) => {
        const [sid, date] = k.split("|");
        return { staff_id: Number(sid), work_date: date, work_code };
      });
      const r = await editScheduleEntries(year, month, changes);
      setResult(r);
      // 표에서 연차 칸을 바꾸면 사용연차가 같이 가감되므로 잔여연차도 다시 불러온다
      getLeavePlan(year, month).then(setLeavePlan).catch(() => {});
      setEdits({});
      setError("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSavingEdits(false);
    }
  }

  async function handleShare() {
    setSharing(true);
    try {
      const { published_at } = await shareSchedule(year, month);
      setError("");
      // 서버가 상태를 "confirmed" 로 바꾸고 공개 시각을 남겼으므로 화면에도 바로 반영 (재조회 없이).
      setResult((r) => (r ? { ...r, status: "confirmed", published_at } : r));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSharing(false);
    }
  }

  async function handleDownloadImage() {
    if (!gridRef.current) return;
    setDownloading(true);
    try {
      const el = gridRef.current;
      // gridRef 는 overflow-x-auto 라 화면엔 스크롤해야 보이는 날짜도 있다 —
      // 캡처된 이미지는 스크롤 없이 한 달 전체가 다 나오게, 클론에서만
      // overflow 를 풀고 실제 콘텐츠 너비(scrollWidth)로 캡처한다.
      const canvas = await html2canvas(el, {
        backgroundColor: "#ffffff",
        scale: 2,
        width: el.scrollWidth,
        height: el.scrollHeight,
        windowWidth: el.scrollWidth,
        onclone: (_doc, clonedEl) => {
          clonedEl.style.overflow = "visible";
          clonedEl.style.width = `${el.scrollWidth}px`;
        },
      });
      const url = canvas.toDataURL("image/png");
      const a = document.createElement("a");
      a.href = url;
      a.download = `메밀집_스케줄_${year}-${String(month).padStart(2, "0")}.png`;
      a.click();
    } catch {
      setError("이미지 생성에 실패했습니다.");
    } finally {
      setDownloading(false);
    }
  }

  const years = [now.getFullYear(), now.getFullYear() + 1];
  const shownWarnings = result?.warnings.slice(0, 25) ?? [];
  const editLocked = isManualEditBlocked(year, month);

  return (
    <div>
      <div className="mb-4 flex items-center gap-2 text-sm text-gray-500">
        <Link to="/admin" className="hover:underline">
          관리자 홈
        </Link>
        <span>/</span>
        <span className="text-gray-800">근무표 관리</span>
      </div>

      <h1 className="mb-1 text-xl font-bold">근무표 관리</h1>
      <p className="mb-4 text-sm text-gray-500">
        “자동배치 실행”으로 근무표를 만들 수 있으며, 표의 칸을 클릭해 직접 고칠 수
        있습니다. 완성되면 “직원에게 공개”를 눌러주세요.
      </p>

      {/* 컨트롤 */}
      <div className="mb-4 space-y-4 rounded-lg border bg-white p-4">
        <div className="flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-xs text-gray-600">연도</span>
          <select
            className="rounded border border-gray-300 px-3 py-2 text-sm"
            value={year}
            onChange={(e) => onPeriodChange(Number(e.target.value), month)}
          >
            {years.map((y) => (
              <option key={y} value={y}>
                {y}년
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-xs text-gray-600">월</span>
          <select
            className="rounded border border-gray-300 px-3 py-2 text-sm"
            value={month}
            onChange={(e) => onPeriodChange(year, Number(e.target.value))}
          >
            {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
              <option key={m} value={m}>
                {m}월
              </option>
            ))}
          </select>
        </label>
        </div>

        {/* 이번 달 연차 사용 개수: [잔여연차] [이름] [개수] — 날짜는 자동배치가 랜덤으로 골라 넣는다 */}
        {leavePlan.length > 0 && (
          <div>
            <div className="mb-1.5 flex flex-wrap items-baseline gap-2">
              <h2 className="text-sm font-semibold text-gray-700">이번 달 연차 사용 개수</h2>
              <span className="text-xs text-gray-400">
                적은 개수만큼 자동배치가 인원이 부족하지 않은 날에 알아서 넣습니다. 실행하면
                사용연차에서 차감돼요.
              </span>
            </div>
            <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {leavePlan.map((r) => {
                const err = leaveInputError(r);
                return (
                  <li
                    key={r.staff_id}
                    className="flex items-center gap-2 rounded border bg-gray-50 px-3 py-2"
                  >
                    <span
                      className="w-14 shrink-0 rounded bg-white px-1.5 py-0.5 text-center text-xs text-gray-600"
                      title="사용 가능한 잔여연차"
                    >
                      잔여 {Number.isInteger(r.remaining) ? r.remaining : r.remaining.toFixed(1)}
                    </span>
                    <span className="min-w-0 flex-1 truncate text-sm font-medium">
                      {r.staff_name}
                    </span>
                    <input
                      type="number"
                      min="0"
                      step="1"
                      inputMode="numeric"
                      value={leaveInputs[r.staff_id] ?? ""}
                      onChange={(e) =>
                        setLeaveInputs((prev) => ({ ...prev, [r.staff_id]: e.target.value }))
                      }
                      placeholder="0"
                      className={
                        "w-16 rounded border px-2 py-1.5 text-right text-base sm:text-sm " +
                        (err ? "border-red-400" : "border-gray-300")
                      }
                    />
                    <span className="min-w-8 shrink-0 whitespace-nowrap text-xs text-gray-500">
                      {err ? <span className="text-red-600">{err}</span> : "개"}
                    </span>
                  </li>
                );
              })}
            </ul>
          </div>
        )}

        {/* 이번 달 주방 로테이션: 전월 담당 기준으로 오픈→미들→마감→오픈 한 칸씩 이동 */}
        {rotation.length > 0 && (
          <div>
            <div className="mb-1.5 flex flex-wrap items-baseline gap-2">
              <h2 className="text-sm font-semibold text-gray-700">이번 달 주방 로테이션</h2>
              <span className="text-xs text-gray-400">
                {rotationSaved && !rotationEdited
                  ? "저장된 값이에요."
                  : "전월 담당 기준으로 자동 계산한 값이에요. 바꾸면 실행할 때 저장됩니다."}{" "}
                연차·사전휴무로 못 나오는 날만 다른 사람이 대신 채워요.
              </span>
            </div>
            <ul className="flex flex-wrap gap-2">
              {rotation.map((r) => (
                <li
                  key={r.staff_id}
                  className="flex items-center gap-2 rounded border bg-gray-50 px-3 py-2"
                >
                  <span className="text-sm font-medium">{r.staff_name}</span>
                  <select
                    value={r.position}
                    onChange={(e) => setRotationSlot(r.staff_id, e.target.value as RotationSlot)}
                    className="rounded border border-gray-300 px-2 py-1 text-base sm:text-sm"
                  >
                    {(Object.keys(SLOT_LABEL) as RotationSlot[]).map((k) => (
                      <option key={k} value={k}>
                        {SLOT_LABEL[k]}
                      </option>
                    ))}
                  </select>
                </li>
              ))}
            </ul>
            {rotationDuplicate && (
              <p className="mt-1 text-xs text-red-600">
                오픈·미들·마감을 한 명씩 겹치지 않게 골라 주세요.
              </p>
            )}
          </div>
        )}

        <div className="flex flex-wrap items-end gap-3">
        <button
          onClick={handleRun}
          disabled={running || leaveHasError || rotationDuplicate || isAutoScheduleBlocked(year, month)}
          title={
            isAutoScheduleBlocked(year, month)
              ? "이번 달과 그 이전 달은 자동배치를 다시 실행할 수 없습니다. 다음 달 스케줄부터 가능해요."
              : ""
          }
          className="rounded bg-primary hover:bg-primary-dark px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {running ? "계산 중…" : "자동배치 실행"}
        </button>
        {result?.saved && (
          <button
            onClick={handleShare}
            disabled={sharing || dirtyCount > 0}
            title={dirtyCount > 0 ? "먼저 수정을 저장하세요" : ""}
            className="rounded border border-gray-300 px-4 py-2 text-sm font-medium disabled:opacity-50"
          >
            {sharing ? "공개 중…" : "직원에게 공개"}
          </button>
        )}
        {result?.saved && result.status === "confirmed" && (
          <button
            onClick={handleDownloadImage}
            disabled={downloading}
            title="확정된 스케줄을 이미지(PNG)로 저장"
            className="rounded border border-gray-300 px-4 py-2 text-sm font-medium disabled:opacity-50"
          >
            {downloading ? "생성 중…" : "이미지 다운로드"}
          </button>
        )}
        {result?.saved && (
          <span
            className={
              "rounded-full px-2 py-0.5 text-xs font-semibold " +
              (result.status === "confirmed"
                ? "bg-mint text-mint-ink"
                : "bg-amber-100 text-amber-800")
            }
          >
            {result.status === "confirmed" ? "공유됨 (직원에게 노출)" : "임시 (직원에게 안 보임)"}
          </span>
        )}
        {result?.status === "confirmed" && result.published_at && (
          <span className="text-xs text-gray-400">
            {fmtPublishedAt(result.published_at)} 공개
          </span>
        )}
        {result?.saved && (
          <span className="text-xs text-gray-400">
            {result.solve_seconds > 0 && <>계산 {result.solve_seconds}s · </>}
            {result.edited && (
              <span className="text-amber-600">수동 수정본 · </span>
            )}
            {result.feasible ? (
              <span className="text-mint-ink">모든 조건 충족</span>
            ) : (
              <span className="text-red-600">조건 미충족 (경고 확인)</span>
            )}
          </span>
        )}
        </div>
      </div>

      {isAutoScheduleBlocked(year, month) && (
        <p className="mb-4 text-sm text-amber-700">
          이번 달과 그 이전 달은 자동배치를 다시 실행할 수 없습니다. 다음 달
          스케줄부터 가능해요. (급한 변경은 표의 칸을 직접 클릭해서 수정하세요.)
        </p>
      )}
      {isManualEditBlocked(year, month) && (
        <p className="mb-4 text-sm text-red-600">
          이전 달 스케줄은 더 이상 수정할 수 없습니다.
        </p>
      )}

      {error && (
        <p className="mb-4 rounded bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      {/* 경고 */}
      {result && result.warnings.length > 0 && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm">
          <div className="mb-1 font-medium text-red-800">
            경고 {result.warnings.length}건 (인원 부족 / 기본휴무 미달 / 관리
            책임자 / 연속근무 등)
          </div>
          <ul className="max-h-48 space-y-0.5 overflow-y-auto text-red-700">
            {shownWarnings.map((w, i) => (
              <li key={i}>· {w.message}</li>
            ))}
            {result.warnings.length > shownWarnings.length && (
              <li>… 외 {result.warnings.length - shownWarnings.length}건</li>
            )}
          </ul>
        </div>
      )}

      {/* 수정 저장 바 */}
      {dirtyCount > 0 && (
        <div className="mb-3 flex items-center gap-3 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm">
          <span className="font-medium text-amber-800">
            {dirtyCount}칸 수정됨 (아직 저장 안 됨)
          </span>
          <button
            onClick={saveEdits}
            disabled={savingEdits}
            className="rounded bg-primary hover:bg-primary-dark px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50"
          >
            {savingEdits ? "저장 중…" : "수정 저장"}
          </button>
          <button
            onClick={() => setEdits({})}
            className="text-xs text-gray-500 hover:underline"
          >
            되돌리기
          </button>
        </div>
      )}

      {/* 표 */}
      {loading ? (
        <p className="text-sm text-gray-400">불러오는 중…</p>
      ) : !result ? (
        <p className="rounded-lg border bg-white p-6 text-center text-sm text-gray-400">
          {year}년 {month}월 스케줄이 아직 없습니다. “자동배치 실행”을 눌러 만들어
          보세요.
        </p>
      ) : result.rows.length === 0 ? (
        <p className="rounded-lg border bg-white p-6 text-center text-sm text-gray-400">
          등록된 직원이 없습니다. 먼저{" "}
          <Link to="/admin/staff" className="underline">
            직원 등록
          </Link>
          을 해주세요.
        </p>
      ) : (
        <>
          <Legend />
          <div ref={gridRef} className="overflow-x-auto rounded-lg border bg-white">
            <table className="border-collapse text-xs">
              <thead>
                <tr className="border-b bg-gray-50">
                  <th className="sticky left-0 z-10 bg-gray-50 px-3 py-2 text-left font-medium">
                    직원
                  </th>
                  {result.days.map((d) => {
                    const wd = parseWd(d);
                    const dayNum = Number(d.split("-")[2]);
                    const weekend = wd === 0 || wd === 6;
                    const holidayName = holidays[d];
                    return (
                      <th
                        key={d}
                        title={holidayName}
                        className={
                          "w-8 px-0 py-1 text-center font-medium " +
                          (holidayName
                            ? "bg-rose-50 text-rose-700"
                            : weekend
                              ? "bg-amber-50 text-amber-700"
                              : "")
                        }
                      >
                        <div>{dayNum}</div>
                        <div className="text-[10px] text-gray-400">
                          {WD_CHAR[wd]}
                        </div>
                        {holidayName && (
                          <div className="line-clamp-2 px-0.5 text-[7px] leading-tight break-all text-rose-600">
                            {holidayName}
                          </div>
                        )}
                      </th>
                    );
                  })}
                </tr>
              </thead>
              <tbody>
                {result.rows.map((row) => (
                  <tr key={row.staff_id} className="border-b last:border-0">
                    <td className="sticky left-0 z-10 bg-white px-3 py-1 whitespace-nowrap">
                      <span className="font-medium">{row.staff_name}</span>
                      <span className="ml-1 text-[10px] text-gray-400">
                        {LABEL.position[row.position] ?? row.position}
                        {row.role === "owner" ? " · 사장님" : ""}
                        {row.role === "manager" ? " · 점장" : ""}
                      </span>
                    </td>
                    {result.days.map((d) => {
                      const key = cellKey(row.staff_id, d);
                      const original = row.cells[d] ?? "";
                      const code = edits[key] ?? original;
                      const meta = CELL[code];
                      const dirty = key in edits;

                      if (editingCell === key && !editLocked) {
                        return (
                          <td key={d} className="w-8 border-l p-0 text-center">
                            <select
                              autoFocus
                              defaultValue={code}
                              onBlur={() => setEditingCell(null)}
                              onChange={(e) =>
                                pickCode(key, e.target.value, original)
                              }
                              className="w-full bg-white text-[11px]"
                            >
                              {EDIT_CODES.map((c) => (
                                <option key={c} value={c}>
                                  {c}
                                </option>
                              ))}
                            </select>
                          </td>
                        );
                      }
                      return (
                        <td
                          key={d}
                          title={
                            editLocked
                              ? `${d} ${code} — 이전 달 스케줄은 수정할 수 없습니다.`
                              : `${d} ${code} — 클릭해서 수정`
                          }
                          onClick={editLocked ? undefined : () => setEditingCell(key)}
                          className={
                            "w-8 border-l px-0.5 py-1 text-center" +
                            (editLocked
                              ? " cursor-not-allowed opacity-60"
                              : " cursor-pointer hover:outline hover:outline-1 hover:outline-gray-400") +
                            (dirty ? " outline outline-2 outline-amber-500" : "")
                          }
                        >
                          {meta ? (
                            <span
                              className={
                                "inline-block w-full rounded-full px-1 py-0.5 text-[11px] leading-none font-semibold " +
                                meta.cls
                              }
                            >
                              {meta.short}
                            </span>
                          ) : (
                            <span className="text-gray-300">·</span>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="border-t-2 bg-gray-50 font-medium">
                  <td className="sticky left-0 z-10 bg-gray-50 px-3 py-1 whitespace-nowrap">
                    총근무인원
                  </td>
                  {result.days.map((d) => (
                    <td key={d} className="w-8 border-l px-0.5 py-1 text-center">
                      {dayStats[d]?.total ?? 0}
                    </td>
                  ))}
                </tr>
                <tr className="bg-gray-50 font-medium">
                  <td className="sticky left-0 z-10 bg-gray-50 px-3 py-1 whitespace-nowrap">
                    주방인원
                  </td>
                  {result.days.map((d) => (
                    <td key={d} className="w-8 border-l px-0.5 py-1 text-center">
                      {dayStats[d]?.kitchen ?? 0}
                    </td>
                  ))}
                </tr>
                <tr className="bg-gray-50 font-medium">
                  <td className="sticky left-0 z-10 bg-gray-50 px-3 py-1 whitespace-nowrap">
                    홀인원
                  </td>
                  {result.days.map((d) => (
                    <td key={d} className="w-8 border-l px-0.5 py-1 text-center">
                      {dayStats[d]?.hall ?? 0}
                    </td>
                  ))}
                </tr>
              </tfoot>
            </table>
          </div>
          <p className="mt-2 text-xs text-gray-400">
            칸을 클릭하면 근무 코드를 바꿀 수 있습니다. 필요인원 부족·초과 경고는 저장할
            때마다 다시 계산되고, 기본휴무·연속근무 경고는 자동배치 직후에만 나옵니다.
          </p>

          <ShiftDistribution rows={result.rows} />
        </>
      )}
    </div>
  );
}

function Legend() {
  const pill = "rounded-full px-1.5 py-0.5 font-semibold";
  return (
    <div className="mb-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-gray-500">
      <span className="font-medium text-gray-600">홀:</span>
      <span>
        <span className={pill + " bg-fo text-fo-ink"}>FO</span> 홀오픈
      </span>
      <span>
        <span className={pill + " bg-fc text-fc-ink"}>FC</span> 홀마감
      </span>
      <span className="ml-2 font-medium text-gray-600">주방:</span>
      <span>
        <span className={pill + " bg-bo text-bo-ink"}>BO</span> 주방오픈
      </span>
      <span>
        <span className={pill + " bg-bm text-bm-ink"}>BM</span> 주방미들
      </span>
      <span>
        <span className={pill + " bg-bc text-bc-ink"}>BC</span> 주방마감
      </span>
      <span className="ml-2">
        <span className={pill + " bg-full text-full-ink"}>풀</span> 풀오마
      </span>
      <span>
        <span className={pill + " bg-off text-off-ink"}>휴</span> 휴무
      </span>
      <span>
        <span className={pill + " bg-leave text-leave-ink"}>연</span> 연차
      </span>
      <span>
        <span className={pill + " bg-dayoff text-dayoff-ink"}>사</span> 사전휴무
      </span>
    </div>
  );
}

// 직원별 근무 유형 분포 (오픈/미들/마감 몰아주기 방지 확인용)
const POS_KO: Record<string, string> = {
  hall: "홀 전담",
  kitchen: "주방 전담",
  both: "겸직",
};

function ShiftDistribution({ rows }: { rows: ScheduleRow[] }) {
  const regulars = rows.filter(
    (r) => r.role === "staff" && r.employment_type === "full_time",
  );
  const gap = (a: number[]) => (a.length ? Math.max(...a) - Math.min(...a) : 0);
  const range = (a: number[]) =>
    a.length ? `${Math.min(...a)} ~ ${Math.max(...a)}` : "-";

  const groups = ["hall", "both", "kitchen"]
    .map((p) => ({ pos: p, members: regulars.filter((r) => r.position === p) }))
    .filter((g) => g.members.length >= 2);

  return (
    <div className="mt-6">
      <h2 className="mb-1 text-sm font-bold">직원별 근무 유형 분포</h2>
      <p className="mb-2 text-xs text-gray-500">
        “홀/주방”은 그달 각 포지션에서 근무한 일수입니다. 같은 포지션의 일반
        직원끼리 오픈·마감이 한쪽으로 쏠리지 않게 분산합니다. (사장님·점장은 항상
        마감 고정이라 공정성 대상 제외)
      </p>
      <div className="mb-2 flex flex-wrap gap-2 text-xs">
        {groups.map((g) => (
          <span key={g.pos} className="rounded bg-gray-100 px-2 py-1">
            {POS_KO[g.pos]} — 오픈{" "}
            <b>{range(g.members.map((m) => m.summary.open))}</b> (편차{" "}
            {gap(g.members.map((m) => m.summary.open))}) · 마감{" "}
            <b>{range(g.members.map((m) => m.summary.close))}</b> (편차{" "}
            {gap(g.members.map((m) => m.summary.close))})
          </span>
        ))}
      </div>
      <div className="overflow-x-auto rounded-lg border bg-white">
        <table className="w-full text-sm">
          <thead className="border-b bg-gray-50 text-left text-gray-500">
            <tr>
              <th className="px-3 py-2">직원</th>
              <th className="px-3 py-2 text-right">홀</th>
              <th className="px-3 py-2 text-right">주방</th>
              <th className="px-3 py-2 text-right">오픈</th>
              <th className="px-3 py-2 text-right">미들</th>
              <th className="px-3 py-2 text-right">마감</th>
              <th className="px-3 py-2 text-right">풀오마</th>
              <th className="px-3 py-2 text-right">근무합</th>
              <th className="px-3 py-2 text-right">휴무</th>
              <th className="px-3 py-2 text-right">연차</th>
              <th className="px-3 py-2 text-right">사휴</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const roleTag =
                r.role === "owner"
                  ? "사장님"
                  : r.role === "manager"
                    ? "점장"
                    : r.employment_type === "part_time"
                      ? "파트"
                      : "";
              return (
                <tr key={r.staff_id} className="border-b last:border-0">
                  <td className="px-3 py-1.5">
                    <span className="font-medium">{r.staff_name}</span>
                    {roleTag && (
                      <span className="ml-1 text-[10px] text-gray-400">
                        {roleTag}
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-1.5 text-right text-fo-ink">
                    {r.summary.hall}
                  </td>
                  <td className="px-3 py-1.5 text-right text-bo-ink">
                    {r.summary.kitchen}
                  </td>
                  <td className="px-3 py-1.5 text-right">{r.summary.open}</td>
                  <td className="px-3 py-1.5 text-right">{r.summary.mid}</td>
                  <td className="px-3 py-1.5 text-right">{r.summary.close}</td>
                  <td className="px-3 py-1.5 text-right">{r.summary.full}</td>
                  <td className="px-3 py-1.5 text-right font-semibold">
                    {r.summary.work}
                  </td>
                  <td className="px-3 py-1.5 text-right text-gray-500">
                    {r.summary.off}
                  </td>
                  <td className="px-3 py-1.5 text-right text-gray-500">
                    {r.summary.leave}
                  </td>
                  <td className="px-3 py-1.5 text-right text-gray-500">
                    {r.summary.blocked}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
