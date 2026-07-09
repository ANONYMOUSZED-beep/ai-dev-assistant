"use client";

import Spline from "@splinetool/react-spline";
import { useState } from "react";

import { disableSplineWatermark } from "@/lib/spline";

/**
 * Interactive 3D robot shown in the source-viewer panel while it's idle
 * (no citation/file open). It reacts to the cursor. Fades in once loaded so
 * there's no abrupt pop.
 */
export default function SplineRobot() {
  const [loaded, setLoaded] = useState(false);

  return (
    <div className={`spline-robot ${loaded ? "spline-robot--loaded" : ""}`}>
      <Spline
        scene="https://prod.spline.design/OueO3WFd8eZJF3IX/scene.splinecode"
        onLoad={(app) => {
          disableSplineWatermark(app);
          setLoaded(true);
        }}
      />
    </div>
  );
}
