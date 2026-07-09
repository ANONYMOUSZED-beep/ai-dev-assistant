// Helper to disable the built-in "Built with Spline" watermark overlay.
//
// The watermark is rendered inside the WebGL pipeline (not a DOM element), so it
// can't be hidden with CSS. The runtime exposes it via the Application's render
// pipeline (`_renderer.pipeline`), which has both a `setWatermark()` method and a
// `logoOverlayPass.enabled` flag read every frame. We turn both off in `onLoad`.
//
// This touches internal runtime fields, so it's fully guarded: if a future
// package version renames things, nothing throws — the watermark simply remains.

interface SplinePipeline {
  setWatermark?: (value: unknown) => void;
  logoOverlayPass?: { enabled: boolean };
}

interface SplineAppLike {
  _renderer?: { pipeline?: SplinePipeline };
}

export function disableSplineWatermark(app: unknown): void {
  try {
    const pipeline = (app as SplineAppLike)?._renderer?.pipeline;
    if (!pipeline) return;
    if (typeof pipeline.setWatermark === "function") {
      pipeline.setWatermark(null);
    }
    if (pipeline.logoOverlayPass) {
      pipeline.logoOverlayPass.enabled = false;
    }
  } catch {
    // Internal API changed — leave the watermark rather than crash.
  }
}
