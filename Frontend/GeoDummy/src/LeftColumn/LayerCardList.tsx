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
  onSettings: (layerId: string) => void;
}

export default function LayerCardList({ layers, setLayers, onSettings }: Props) {
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const layerIds = useMemo(() => layers.map((l) => l.id), [layers]);

  const handleDragEnd = useCallback(
    ({ active, over }: DragEndEvent) => {
      if (!over || active.id === over.id) return;

      setLayers((prev) => {
        const oldIndex = prev.findIndex((l) => l.id === active.id);
        const newIndex = prev.findIndex((l) => l.id === over.id);

        return arrayMove(prev, oldIndex, newIndex);
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
        {layers.map((layer) => (
          <LayerCard key={layer.id} layer={layer} onSettings={onSettings} />
        ))}
      </SortableContext>
    </DndContext>
  );
}
