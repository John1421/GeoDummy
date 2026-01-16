import { useState, useRef } from "react";
import { colors, typography, radii, shadows } from "../Design/DesignTokens";
import { FileCode, Play, Square } from "lucide-react";
import { ThreeDot } from "react-loading-indicators"
import RunScriptWindow from "./RunScriptWindow";
import type { BackendLayerMetadata } from "../LeftColumn/LayerSidebar";

interface ScriptCardProps {
  id: string;
  name: string;
  description: string;
  loading: boolean;
  setLoading: (loading: boolean) => void;
  onAddLayer: (layer_id: string, metadata: BackendLayerMetadata) => Promise<void>;
}

function ScriptCard({ id, name, description, loading, setLoading, onAddLayer }: ScriptCardProps) {
  const [isRunScriptWindowOpen, setIsRunScriptWindowOpen] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  const handleRun = () => {
    setIsRunScriptWindowOpen(true);
  };

  const handleStop = async () => {
    // Abort the ongoing fetch request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

    try {
      const response = await fetch(`http://localhost:5050/execute_script/${id}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        const data = await response.json();
        console.log('Script stopped:', data.message);
      } else {
        const errorData = await response.json().catch(() => null);
        console.error('Failed to stop script:', errorData);
      }
    } catch (err) {
      console.error('Error stopping script:', err);
    } finally {
      setLoading(false);
    }
  };

  // Mock de execução no backend recebendo o scriptId
  // async function runScriptMock(
  //   scriptId: string,
  //   payload: { inputFilePath: string; numberValue: number; listValue: number[] }
  // ): Promise<{ status: string; output: string }>{
  //   console.log("▶️ Mock run: sending to backend", { scriptId, payload });
  //   // Simula latência
  //   await new Promise(r => setTimeout(r, 800));
  //   // Simula resposta
  //   return { status: "ok", output: `Script ${scriptId} executed with ${payload.listValue.length} items` };
  // }

  // const handleRunScriptFromWindow = async (
  //   scriptId: string,
  //   inputFilePath: string,
  //   numberValue: number,
  //   listValue: number[]
  // ) => {
  //   setLoading(true);
  //   try {
  //     const res = await runScriptMock(scriptId, { inputFilePath, numberValue, listValue });
  //     console.log("✅ Mock result:", res);
  //   } finally {
  //     setLoading(false);
  //   }
  // };

  return (
    <div
      style={{
        width: "100%",
        backgroundColor: colors.cardBackground,
        border: `1px solid ${colors.borderStroke}`,
        borderRadius: radii.md,
        padding: 12,
        boxShadow: shadows.none,
        transition: "box-shadow 0.2s ease",
        fontFamily: typography.normalFont,
      }}
    >
      <div style={{ display: "flex", flexDirection: "column", rowGap: 4 }}>
        <h3
          style={{
            margin: 0,
            display: "flex",
            alignItems: "center",
            gap: 8,
            fontWeight: 600,
            fontSize: typography.sizeMd,
            color: colors.sidebarForeground,
            fontFamily: typography.normalFont,
          }}
        >
          <FileCode size={16} style={{ color: colors.sidebarForeground }} />
          {name}
        </h3>

        <p
          style={{
            fontSize: typography.sizeSm,
            color: colors.sidebarForeground,
            margin: 0,
            opacity: 0.8,
          }}
        >
          {description}
        </p>

        <button
          onClick={handleRun}
          disabled={loading}
          style={{
            marginTop: 8,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "6px 12px",
            backgroundColor: loading ? colors.borderStroke : colors.primary,
            color: loading ? colors.sidebarForeground : "white",
            border: "none",
            borderRadius: radii.sm,
            fontSize: typography.sizeSm,
            cursor: loading ? "default" : "pointer",
            opacity: loading ? 0.8 : 1,
            transition: "0.2s",
            height: 32,
          }}
        >
          {loading ? (
            <ThreeDot
              color="#ffffff"
              size="small"
              text=""
              textColor=""
            />
          ) : (
            <>
              <Play size={16} style={{ marginRight: 8 }} />
              Run Script
            </>
          )}
        </button>

        {loading && (
          <button
            onClick={handleStop}
            style={{
              marginTop: 8,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              padding: "6px 12px",
              backgroundColor: "#DC2626",
              color: "white",
              border: "none",
              borderRadius: radii.sm,
              fontSize: typography.sizeSm,
              cursor: "pointer",
              transition: "0.2s",
              height: 32,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = "#B91C1C";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = "#DC2626";
            }}
          >
            <Square size={16} style={{ marginRight: 8 }} />
            Stop Script
          </button>
        )}
      </div>
      <RunScriptWindow
        isOpen={isRunScriptWindowOpen}
        onClose={() => setIsRunScriptWindowOpen(false)}
        scriptId={id}
        onAddLayer={onAddLayer}
        onScriptStart={() => setLoading(true)}
        onScriptEnd={() => setLoading(false)}
        abortControllerRef={abortControllerRef}
      />
    </div>
  );
}

export default ScriptCard;
