import { useCallback, useState } from "react";
import { Wrench as ToolsIcon } from "lucide-react";
import SidebarPanel from "../TemplateModals/SidebarModal";
import { colors } from "../Design/DesignTokens";

import ToolCategoryToggle from "./ToolCategoryToggle";
import ScriptCard from "./ScriptCard";
import AddNewScript from "./AddNewScript";

export interface Script {
  id: string;
  name: string;
  description?: string;
  fileName?: string;
  category?: string;
  number?: string;
  type?: string;
}

const EXAMPLE_SCRIPTS: Script[] = [
  {
    id: "1",
    category: "Category 1",
    name: "Tree Height Analysis",
    description: "Analysis of tree heights on a selected layer.",
  },
  {
    id: "2",
    category: "Category 1",
    name: "Simplify Geometry",
    description: "Reduces geometry complexity.",
  },
  {
    id: "3",
    category: "Category 2",
    name: "Buffer Zones",
    description: "Creates buffer zones around features.",
  },
  {
    id: "4",
    category: "Category 2",
    name: "Spatial Join",
    description: "Joins attributes based on spatial relationships.",
  },
];

export default function ScriptList() {
  const [showAddNew, setShowAddNew] = useState(false);
  const [scripts, setScripts] = useState<Script[]>(EXAMPLE_SCRIPTS);

  const handleAddScript = useCallback(
    (fileName: string, category: string, number: string, type: string) => {
      // Extract name from filename (remove extension)
      const scriptName = fileName.replace(/\.[^/.]+$/, "");

      const newScript: Script = {
        id: crypto.randomUUID(),
        name: scriptName,
        description: `${category} - ${type}`,
        fileName,
        category,
        number,
        type,
      };

      setScripts((prev) => [newScript, ...prev]);
    },
    []
  );

  return (
    <>
      <SidebarPanel
        side="right"
        title="Tools"
        icon={<ToolsIcon size={18} color={colors.primary} />}
        expandedWidthClassName="w-72"
        collapsedWidthClassName="w-12"
        onAdd={() => setShowAddNew(true)}
      >
        {showAddNew && (
          <AddNewScript
            onClose={() => setShowAddNew(false)}
            onAddScript={handleAddScript}
          />
        )}

        {/* TOOL CATEGORIES */}
        <ToolCategoryToggle title="Category 1">
          {scripts
            .filter((s) => s.category === "Category 1" || !s.category)
            .map((script) => (
              <ScriptCard
                key={script.id}
                name={script.name}
                description={script.description || ""}
              />
            ))}
        </ToolCategoryToggle>

        <ToolCategoryToggle title="Category 2">
          {scripts
            .filter((s) => s.category === "Category 2")
            .map((script) => (
              <ScriptCard
                key={script.id}
                name={script.name}
                description={script.description || ""}
              />
            ))}
        </ToolCategoryToggle>
      </SidebarPanel>
    </>
  );
}
