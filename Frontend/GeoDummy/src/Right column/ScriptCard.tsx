import { colors, typography, radii, shadows } from "../Design/DesignTokens";
import {FileCode, Play} from "lucide-react";

interface ScriptCardProps {
  name: string;
  description: string;
}

function ScriptCard({ name, description }: ScriptCardProps) {
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
          style={{
            marginTop: 8,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "6px 12px",
            backgroundColor: colors.primary,
            color: "white",
            border: "none",
            borderRadius: radii.sm,
            fontSize: typography.sizeSm,
            cursor: "pointer",
          }}
        >
          <Play size={16} style={{ marginRight: 8 }} />
          Run Script
        </button>
      </div>
    </div>
  );
}

export default ScriptCard;
