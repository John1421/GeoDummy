import { useCallback, useState, useEffect } from "react";
import { Wrench as ToolsIcon } from "lucide-react";
import SidebarPanel from "../TemplateModals/SidebarModal";
import { colors, icons } from "../Design/DesignTokens";

import ToolCategoryToggle from "./ToolCategoryToggle";
import ScriptCard from "./ScriptCard";
import AddNewScript from "./AddNewScript";
import { type BackendLayerMetadata } from "../LeftColumn/LayerSidebar";

export interface Script {
  id: string;
  name: string;
  description?: string;
  category?: string;
}

// const EXAMPLE_SCRIPTS: Script[] = [
//   {
//     id: "1",
//     category: "Category 1",
//     name: "Tree Height Analysis",
//     description: "Analysis of tree heights on a selected layer.",
//   },
//   {
//     id: "2",
//     category: "Category 1",
//     name: "Simplify Geometry",
//     description: "Reduces geometry complexity.",
//   },
//   {
//     id: "3",
//     category: "Category 2",
//     name: "Buffer Zones",
//     description: "Creates buffer zones around features.",
//   },
//   {
//     id: "4",
//     category: "Category 2",
//     name: "Spatial Join",
//     description: "Joins attributes based on spatial relationships.",
//   },
// ];

interface ScriptListProps {
  onAddLayer: (layer_id: string, metadata: BackendLayerMetadata) => Promise<void>;
}

export default function ScriptList({ onAddLayer }: ScriptListProps) {
  const [showAddNew, setShowAddNew] = useState(false);
  const [scripts, setScripts] = useState<Script[]>([]);
  const [loadingScripts, setLoadingScripts] = useState<Record<string, boolean>>({});

  // Fetch scripts from backend on mount
  useEffect(() => {
    const fetchScripts = async () => {
      try {
        const response = await fetch("http://localhost:5050/scripts");
        
        if (!response.ok) {
          throw new Error("Error retrieving scripts");
        }

        const data = await response.json();
        const { scripts_ids, scripts_metadata } = data;

        // Transform the response into Script objects
        const fetchedScripts: Script[] = scripts_ids.map((id: string, index: number) => {
          const metadata = scripts_metadata[index] || {};
          return {
            id,
            name: metadata.name || id,
            description: metadata.description || "",
            category: metadata.category || "Uncategorized",
          };
        });

        setScripts(fetchedScripts);
      } catch (err) {
        console.error("Failed to fetch scripts", err);
      }
    };

    fetchScripts();
  }, []);

  const handleAddScript = useCallback(
    (id: string, name: string, category: string, description: string) => {
      const cleanCategory =
        category.trim().length > 0
          ? category.trim().replace(/\s+/g, " ").toLowerCase()
          : "uncategorized";

      const formattedCategory =
        cleanCategory.charAt(0).toUpperCase() + cleanCategory.slice(1);

      const newScript: Script = {
        id,
        name,
        description,
        category: formattedCategory,
      };

      setScripts(prev => [newScript, ...prev]);
    },
    []
  );


  const categories = Array.from(
    new Set(
      scripts.map((s) =>
        (s.category ?? "Uncategorized").trim().replace(/\s+/g, " ").toLowerCase()
      )
    )
  )
    .map(c => c.charAt(0).toUpperCase() + c.slice(1))
    .sort();


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
            existingCategories={categories}
          />
        )}

        {/* Renderização automática das categorias */}
        {categories.map((category) => (
          <ToolCategoryToggle key={category} title={category}>
            {scripts
              .filter((script) => script.category?.toLowerCase() === category.toLowerCase())
              .slice()
              .sort((a, b) => a.name.localeCompare(b.name, "pt", { sensitivity: "base" }))
              .map((script) => (
                <ScriptCard
                  key={script.id}
                  id={script.id}
                  name={script.name}
                  description={script.description || ""}
                  loading={loadingScripts[script.id] || false}
                  setLoading={(loading) =>
                    setLoadingScripts(prev => ({ ...prev, [script.id]: loading }))
                  }
                  onAddLayer={onAddLayer}
                />
              ))}
          </ToolCategoryToggle>
        ))}
      </SidebarPanel>
    </>
  );
}
