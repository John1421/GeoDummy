import { useState } from "react";
import { colors, typography, radii, shadows } from "../Design/DesignTokens";
import { FileCode, Play } from "lucide-react";

interface ScriptCardProps {
  name: string;
  description: string;
}

function ScriptCard({ name, description }: ScriptCardProps) {
  const [loading, setLoading] = useState(false);

  const handleRun = () => {
    setLoading(true);

    // Simulação de tempo de execução (substituir com lógica real)
    setTimeout(() => {
      setLoading(false);
    }, 2000);
  };

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
          }}
        >
          {loading ? (
            "Loading..."
          ) : (
            <>
              <Play size={16} style={{ marginRight: 8 }} />
              Run Script
            </>
          )}
        </button>
      </div>
    </div>
  );
}

export default ScriptCard;
