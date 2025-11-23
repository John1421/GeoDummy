import { useState } from "react";
import { Wrench as ToolsIcon } from "lucide-react";
import SidebarPanel from "../TemplateModals/SidebarModal";
import { colors } from "../Design/DesignTokens";

import ToolCategoryToggle from "./ToolCategoryToggle";
import ScriptCard from "./ScriptCard";
import AddNewScript from "../Additional windows/AddNewScript";

export default function ScriptList() {
  const [showAddNew, setShowAddNew] = useState(false);

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
          <AddNewScript onClose={() => setShowAddNew(false)} />
        )}

        {/* TOOL CATEGORIES */}
        <ToolCategoryToggle title="Category 1">
          <ScriptCard
            name="Tree Height Analysis"
            description="Analysis of tree heights on a selected layer."
          />
          <ScriptCard
            name="Simplify Geometry"
            description="Reduces geometry complexity."
          />
        </ToolCategoryToggle>

        <ToolCategoryToggle title="Category 2">
          <ScriptCard
            name="Buffer Zones"
            description="Creates buffer zones around features."
          />
          <ScriptCard
            name="Spatial Join"
            description="Joins attributes based on spatial relationships."
          />
        </ToolCategoryToggle>
      </SidebarPanel>
    </>
  );
}
