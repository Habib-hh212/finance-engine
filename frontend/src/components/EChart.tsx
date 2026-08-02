import { useEffect, useRef } from "react";
import ReactECharts from "echarts-for-react";
import type { EChartsOption } from "echarts";

/**
 * Thin wrapper around echarts-for-react that forces a resize() after mount
 * and on every option change. Without this, the chart sometimes initializes
 * against a container that hasn't finished its flex/grid layout pass yet
 * (a well-known ECharts-in-React race), leaving series geometry (bars in
 * particular) painted at zero size while axes/legend still render fine.
 */
export function EChart({ option, height }: { option: EChartsOption; height: number }) {
  const ref = useRef<ReactECharts | null>(null);

  useEffect(() => {
    const id = requestAnimationFrame(() => {
      ref.current?.getEchartsInstance().resize();
    });
    return () => cancelAnimationFrame(id);
  }, [option]);

  return <ReactECharts ref={ref} option={option} style={{ height }} notMerge />;
}
