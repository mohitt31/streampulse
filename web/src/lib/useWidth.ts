import { useEffect, useRef, useState } from "react";

export function useWidth<T extends HTMLElement>(initial = 720) {
  const ref = useRef<T | null>(null);
  const [w, setW] = useState(initial);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver((es) => {
      const cw = es[0]?.contentRect.width;
      if (cw && Math.abs(cw - w) > 1) setW(cw);
    });
    ro.observe(el);
    setW(el.clientWidth || initial);
    return () => ro.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return [ref, w] as const;
}

export function linear(d0: number, d1: number, r0: number, r1: number) {
  const k = d1 === d0 ? 0 : (r1 - r0) / (d1 - d0);
  return (x: number) => r0 + (x - d0) * k;
}

export function niceTicks(lo: number, hi: number, target = 5): number[] {
  const span = hi - lo || 1;
  const raw = span / target;
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const step = [1, 2, 2.5, 5, 10].map((s) => s * mag).find((s) => span / s <= target + 1) ?? raw;
  const out: number[] = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step) out.push(+v.toFixed(6));
  return out;
}

/** SVG path from points; null y breaks the line. */
export function pathOf(pts: [number, number | null][]): string {
  let s = "";
  let pen = false;
  for (const [x, y] of pts) {
    if (y == null || !Number.isFinite(y)) { pen = false; continue; }
    s += `${pen ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`;
    pen = true;
  }
  return s;
}
