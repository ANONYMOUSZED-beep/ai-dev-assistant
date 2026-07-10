"use client";

import Spline from "@splinetool/react-spline";
import { useState } from "react";

import { useSplinePause } from "@/hooks/useSplinePause";
import { disableSplineWatermark } from "@/lib/spline";

/**
 * Interactive 3D robot shown in the source-viewer panel while it's idle
 * (no citation/file open). It reacts to the cursor and fades in once loaded.
 * Its render loop pauses when the panel is hidden/collapsed (perf).
 */
export default function SplineRobot() {
  const [loaded, setLoaded] = useState(false);
  const { appRef, containerRef } = useSplinePause();

  return (
    <div
      ref={containerRef}
      className={`spline-robot ${loaded ? "spline-robot--loaded" : ""}`}
    >
      <Spline
        scene="https://prod.spline.design/OueO3WFd8eZJF3IX/scene.splinecode"
        onLoad={(app) => {
          appRef.current = app;
          disableSplineWatermark(app);
          setLoaded(true);
        }}
      />
    </div>
  );
}
