import { useCallback, useState } from "react";
import { Wrench as ToolsIcon } from "lucide-react";
import SidebarPanel from "../TemplateModals/SidebarModal";
import { colors, icons } from "../Design/DesignTokens";

import ToolCategoryToggle from "./ToolCategoryToggle";
import ScriptCard from "./ScriptCard";
import AddNewScript from "./AddNewScript";

export interface Script {
  id: string;
  name: string;
  description?: string;
  category?: string;
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
    (name: string, category: string) => {
      const newScript: Script = {
        id: crypto.randomUUID(),
        name,
        description: `${category} script`,
        category,
      };

      setScripts(prev => [newScript, ...prev]);
    },
    []
  );

  // 🔥 Extrai categorias automaticamente
  const categories = Array.from(
    new Set(scripts.map((s) => s.category ?? "Uncategorized"))
  );

  return (
    <>
      <SidebarPanel
        side="right"
        title="Tools"
        icon={<ToolsIcon size={icons.size} color={colors.primary} strokeWidth={icons.strokeWidth} />}
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

        {/* 🔥 Renderização automática das categorias */}
        {categories.map((category) => (
          <ToolCategoryToggle key={category} title={category}>
            {scripts
              .filter((script) => script.category === category)
              .map((script) => (
                <ScriptCard
                  key={script.id}
                  name={script.name}
                  description={script.description || ""}
                />
              ))}
          </ToolCategoryToggle>
        ))}
      </SidebarPanel>
    </>
  );
}
