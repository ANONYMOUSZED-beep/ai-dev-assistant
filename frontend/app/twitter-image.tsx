import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "AI Developer Assistant";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function Image() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          padding: "80px",
          backgroundColor: "#1e325a",
          backgroundImage:
            "linear-gradient(135deg, #1e325a 0%, #24407a 55%, #17264a 100%)",
          fontFamily:
            'system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            width: 132,
            height: 132,
            borderRadius: 28,
            backgroundColor: "rgba(255, 255, 255, 0.08)",
            border: "2px solid rgba(169, 182, 214, 0.35)",
            justifyContent: "center",
            marginBottom: 44,
          }}
        >
          <div
            style={{
              display: "flex",
              fontSize: 76,
              fontWeight: 700,
              color: "#ffffff",
              letterSpacing: "-2px",
            }}
          >
            {">_"}
          </div>
        </div>
        <div
          style={{
            display: "flex",
            fontSize: 84,
            fontWeight: 700,
            color: "#ffffff",
            lineHeight: 1.05,
            letterSpacing: "-2px",
          }}
        >
          AI Developer Assistant
        </div>
        <div
          style={{
            display: "flex",
            marginTop: 32,
            fontSize: 38,
            fontWeight: 400,
            color: "#a9b6d6",
            lineHeight: 1.3,
          }}
        >
          Chat with your docs and code — every answer cited.
        </div>
      </div>
    ),
    {
      ...size,
    }
  );
}
