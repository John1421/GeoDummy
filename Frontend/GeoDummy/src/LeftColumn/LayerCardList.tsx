// LayerCardList.tsx
import {
  DndContext,
  closestCenter,
  PointerSensor,
  KeyboardSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";

import {
  arrayMove,
  SortableContext,
  verticalListSortingStrategy,
  sortableKeyboardCoordinates,
} from "@dnd-kit/sortable";

import { useCallback, useMemo } from "react";
import LayerCard from "./LayerCard";
import type { Layer } from "./LayerSidebar";

interface Props {
  layers: Layer[];
  setLayers: React.Dispatch<React.SetStateAction<Layer[]>>;
  onSettings: (layerId: string, rect: DOMRect) => void;
  onToggleVisibility: (layerId: string) => void;
  onRename: (layerId: string, newTitle: string) => void;
  selectedLayerId: string | null;
  onSelectLayer: (id: string) => void;
}

export default function LayerCardList({
  layers,
  setLayers,
  onSettings,
  onToggleVisibility,
  onRename,
  selectedLayerId,
  onSelectLayer,
}: Props) {
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  // Sort by explicit order so top has highest order.
  const sortedLayers = useMemo(() => {
    return [...layers].sort((a, b) => {
      const orderA = typeof a.order === "number" ? a.order : 0;
      const orderB = typeof b.order === "number" ? b.order : 0;

      if (orderA !== orderB) return orderB - orderA;

      // Same order (rare but possible before normalization) → alphabetical
      return a.title.localeCompare(b.title);
    });
  }, [layers]);


  const layerIds = useMemo(
    () => sortedLayers.map((l) => l.id),
    [sortedLayers]
  );

  const handleDragEnd = useCallback(
    ({ active, over }: DragEndEvent) => {
      if (!over || active.id === over.id) return;

      setLayers((prev) => {
        // Work on a sorted copy, then reassign explicit order.
        const sorted = [...prev].sort((a, b) => {
          const orderA = typeof a.order === "number" ? a.order : 0;
          const orderB = typeof b.order === "number" ? b.order : 0;
          return orderB - orderA; // descending
        });

        const oldIndex = sorted.findIndex((l) => l.id === active.id);
        const newIndex = sorted.findIndex((l) => l.id === over.id);

        if (oldIndex === -1 || newIndex === -1) return prev;

        const reordered = arrayMove(sorted, oldIndex, newIndex);
        const len = reordered.length;

        // Assign explicit order so top card has highest order.
        const withOrder = reordered.map((layer, index) => ({
          ...layer,
          order: len - 1 - index,
        }));

        return withOrder;
      });
    },
    [setLayers]
  );

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragEnd={handleDragEnd}
    >
      <SortableContext items={layerIds} strategy={verticalListSortingStrategy}>
        {sortedLayers.map((layer) => (
          <LayerCard
            key={layer.id}
            layer={layer}
            onSettings={onSettings}
            onToggleVisibility={onToggleVisibility}
            onRename={onRename}
            selected={layer.id === selectedLayerId}
            onSelect={() => onSelectLayer(layer.id)}
          />
        ))}
      </SortableContext>
    </DndContext>
  );
}
