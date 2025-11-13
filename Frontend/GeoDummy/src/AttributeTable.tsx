import React, { useState, useMemo, useEffect } from "react";

interface GeoJSONProperties {
  [key: string]: string | number | boolean | null | undefined;
}

interface GeoJSONFeature {
  type: string;
  geometry: any;
  properties: GeoJSONProperties;
}

interface GeoJSONData {
  type: string;
  features: GeoJSONFeature[];
}

interface AttributeTableProps {
  geoData: GeoJSONData | null;
  onRowSelect?: (feature: GeoJSONFeature) => void;
  onSelectionChange?: (selectedFeatures: GeoJSONFeature[]) => void;
}

const AttributeTable: React.FC<AttributeTableProps> = ({
  geoData,
  onRowSelect,
  onSelectionChange,
}) => {
  const [data, setData] = useState<GeoJSONFeature[]>([]);
  const [selectedRows, setSelectedRows] = useState<Set<number>>(new Set());
  const [sortConfig, setSortConfig] = useState<
    { key: string; direction: "asc" | "desc" } | null
  >(null);
  const [isOpen, setIsOpen] = useState(true);

  // Carrega dados
  useEffect(() => {
    if (geoData && geoData.features) setData(geoData.features);
    else setData([]);
  }, [geoData]);

  // Notifica seleções
  useEffect(() => {
    if (onSelectionChange) {
      const selected = Array.from(selectedRows).map((i) => data[i]);
      onSelectionChange(selected);
    }
  }, [selectedRows, data, onSelectionChange]);

  // Ordenação
  const processedData = useMemo(() => {
    let filtered = [...data];

    if (sortConfig?.key) {
      filtered.sort((a, b) => {
        const aVal = a.properties[sortConfig.key];
        const bVal = b.properties[sortConfig.key];

        if (aVal == null) return sortConfig.direction === "asc" ? -1 : 1;
        if (bVal == null) return sortConfig.direction === "asc" ? 1 : -1;
        if (aVal < bVal) return sortConfig.direction === "asc" ? -1 : 1;
        if (aVal > bVal) return sortConfig.direction === "asc" ? 1 : -1;
        return 0;
      });
    }
    return filtered;
  }, [data, sortConfig]);

  const handleSort = (col: string) => {
    setSortConfig((curr) => ({
      key: col,
      direction:
        curr?.key === col && curr.direction === "asc" ? "desc" : "asc",
    }));
  };

  const handleCheckboxChange = (index: number) => {
    setSelectedRows((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  };

  const handleSelectAll = () => {
    if (selectedRows.size === processedData.length) {
      setSelectedRows(new Set());
    } else {
      setSelectedRows(new Set(processedData.map((_, i) => i)));
    }
  };

  // Colunas dinâmicas
  const columns = useMemo(() => {
    if (data.length === 0) return [];
    const keys = new Set<string>();
    data.forEach((f) => Object.keys(f.properties).forEach((k) => keys.add(k)));
    return Array.from(keys);
  }, [data]);

  if (!geoData || data.length === 0) {
    return null;
  }

  // ---------- FECHADO: apenas header ----------
  if (!isOpen) {
    return (
      <div className="flex flex-col justify-end">
        <div className="w-full max-w-[1000px] mx-auto">
          <div
            className="flex items-center justify-between p-3 bg-gray-50 cursor-pointer hover:bg-gray-100 border-t border-x border-gray-300 shadow-lg rounded-t-lg"
            onClick={() => setIsOpen(true)}
          >
            <h3 className="text-sm font-semibold text-gray-800">
              Tabela de Atributos
              {selectedRows.size > 0 && ` (${selectedRows.size} selecionados)`}
            </h3>
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 9l-7 7-7-7"
              />
            </svg>
          </div>
        </div>
      </div>
    );
  }

  // ---------- ABERTO: painel completo ----------
  return (
    <div className="flex justify-center">
      <div className="w-full max-w-[1000px] h-full flex flex-col">
        <div className="border rounded-t-lg bg-white shadow-lg h-full flex flex-col max-h-72">
          {/* Header colapsável */}
          <div
            className="flex items-center justify-between px-3 py-2 bg-gray-50 cursor-pointer hover:bg-gray-100 border-b"
            onClick={() => setIsOpen(false)}
          >
            <h3 className="text-sm font-semibold text-gray-800">
              Tabela de Atributos
              {selectedRows.size > 0 && ` (${selectedRows.size} selecionados)`}
            </h3>
            <svg
              className="w-4 h-4 transform rotate-180"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 9l-7 7-7-7"
              />
            </svg>
          </div>

          {/* Contador */}
          <div className="px-3 py-1 bg-gray-50 border-b">
            <span className="text-xs text-gray-600">
              {processedData.length} de {data.length} elementos
              {selectedRows.size > 0 && ` | ${selectedRows.size} selecionados`}
            </span>
          </div>

          {/* TABELA */}
          <div className="flex-1 overflow-auto">
            <table className="w-full">
              <thead className="bg-gray-100 sticky top-0">
                <tr>
                  <th className="p-2 text-left text-sm font-medium border-b w-12">
                    <input
                      type="checkbox"
                      checked={
                        processedData.length > 0 &&
                        selectedRows.size === processedData.length
                      }
                      onChange={handleSelectAll}
                      className="h-4 w-4"
                    />
                  </th>

                  {columns.map((col) => (
                    <th
                      key={col}
                      onClick={() => handleSort(col)}
                      className="p-2 text-left text-sm font-medium cursor-pointer hover:bg-gray-200 border-b"
                    >
                      <div className="flex items-center">
                        {col}
                        {sortConfig?.key === col && (
                          <span className="ml-1 text-xs">
                            {sortConfig.direction === "asc" ? "↑" : "↓"}
                          </span>
                        )}
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>

              <tbody>
                {processedData.map((feature, idx) => (
                  <tr
                    key={idx}
                    className={`border-b hover:bg-gray-50 cursor-pointer ${
                      selectedRows.has(idx) ? "bg-blue-50" : ""
                    }`}
                    onClick={() => onRowSelect?.(feature)}
                  >
                    <td className="p-2 text-sm">
                      <input
                        type="checkbox"
                        checked={selectedRows.has(idx)}
                        onChange={(e) => {
                          e.stopPropagation();
                          handleCheckboxChange(idx);
                        }}
                        className="h-4 w-4"
                      />
                    </td>

                    {columns.map((col) => (
                      <td key={col} className="p-2 text-sm">
                        {String(feature.properties[col] ?? "")}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AttributeTable;
