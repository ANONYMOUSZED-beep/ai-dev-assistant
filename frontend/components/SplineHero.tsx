"use client";

import Spline from "@splinetool/react-spline";
import { useState } from "react";

import { disableSplineWatermark } from "@/lib/spline";

/**
 * Interactive 3D hero layer that blends into the RIVR video hero.
 *
 * The 3D runtime + scene take a moment to download. To avoid ever showing the
 * bare video ("old design") on its own during that gap, an instant, already-
 * blended CSS poster is server-rendered on top of the video from the very first
 * paint. Once the live scene has loaded, the poster crossfades out and the
 * interactive canvas crossfades in — so on refresh you only ever see the blend.
 */
export default function SplineHero({ scene }: { scene: string }) {
  const [loaded, setLoaded] = useState(false);

  return (
    <div
      className={`hero-spline ${loaded ? "hero-spline--loaded" : ""}`}
      aria-hidden="true"
    >
      {/* Instant blended placeholder — present in the first paint. */}
      <div className="hero-spline__poster" />
      <Spline
        scene={scene}
        onLoad={(app) => {
          disableSplineWatermark(app);
          setLoaded(true);
        }}
      />
    </div>
  );
}
