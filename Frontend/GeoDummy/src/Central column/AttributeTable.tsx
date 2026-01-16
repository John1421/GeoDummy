import React, { useEffect, useMemo, useState } from "react";
interface TableHeader {
  name: string;
  type: string;
  sortable: boolean;
}

interface AttributeTableResponse {
  headers: TableHeader[];
  rows: Record<string, string | number | boolean | null>[];
  total_rows: number;
  warnings?: string[];
}

interface AttributeTableProps {
  layerId: string | null;
}

const AttributeTable: React.FC<AttributeTableProps> = ({ layerId }) => {
  const [data, setData] = useState<AttributeTableResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [isOpen, setIsOpen] = useState(true);
  const [sortConfig, setSortConfig] = useState<{
    key: string;
    direction: "asc" | "desc";
  } | null>(null);

  
  useEffect(() => {
    if (!layerId) {
      setData(null);
      return;
    }

    const controller = new AbortController();

    const fetchAttributeTable = async () => {
      setLoading(true);
      setError(null);

      try {
        const response = await fetch(`http://localhost:5050/layers/${layerId}/table`,
          { signal: controller.signal }
        );

        if (!response.ok) {
          if (response.status === 404) {
            throw new Error("Layer not found");
          }
          throw new Error("Error retrieving attribute table.");
        }

        const result: AttributeTableResponse = await response.json();


        if (!result.headers || !Array.isArray(result.rows)) {
          throw new Error("Invalid response from backend");
        }

        setData(result);
        setLoading(false);
      } catch (err: unknown) {
        if (err instanceof Error) {
          setError(err.message);
        } else {
          setError("Unexpected error");
        }
      }

    };

    fetchAttributeTable();

    return () => controller.abort();
  }, [layerId]);

  /* Ordering  */

  const processedRows = useMemo(() => {
    if (!data) return [];

    const rows = [...data.rows];

    if (sortConfig) {
      rows.sort((a, b) => {
        const aVal = a[sortConfig.key];
        const bVal = b[sortConfig.key];

        if (aVal == null) return sortConfig.direction === "asc" ? -1 : 1;
        if (bVal == null) return sortConfig.direction === "asc" ? 1 : -1;
        if (aVal < bVal) return sortConfig.direction === "asc" ? -1 : 1;
        if (aVal > bVal) return sortConfig.direction === "asc" ? 1 : -1;
        return 0;
      });
    }

    return rows;
  }, [data, sortConfig]);

  const handleSort = (col: string) => {
    setSortConfig((prev) => ({
      key: col,
      direction:
        prev?.key === col && prev.direction === "asc" ? "desc" : "asc",
    }));
  };
  /*const handleCheckboxChange = (index: number) => {
    setSelectedRows((prev) => {
      const next = new Set(prev);

      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }

      return next;
    });
  };


  const handleSelectAll = () => {
    if (!data) return;

    if (selectedRows.size === processedRows.length) {
      setSelectedRows(new Set());
    } else {
      setSelectedRows(new Set(processedRows.map((_, i) => i)));
    }
  };*/


  /*COLLAPSED*/

  if (!isOpen) {
    return (
      <div className="flex flex-col justify-end">
        <div
          className="flex items-center justify-between p-3 bg-gray-50 cursor-pointer hover:bg-gray-100 border-t border-x border-[#DADFE7] shadow-lg"
          onClick={() => setIsOpen(true)}
        >
          <h3 className="text-sm font-semibold text-gray-800">
            Attribute Table
          </h3>
          <span>▲</span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-center">
      <div className="w-full h-full flex flex-col">
        <div className="border bg-white shadow-lg h-full flex flex-col max-h-72 border-[#DADFE7]">
          {/* Header */}
          <div
            className="flex items-center justify-between px-3 py-2 bg-gray-50 cursor-pointer hover:bg-gray-100 border-b border-[#DADFE7]"
            onClick={() => setIsOpen(false)}
          >
            <h3 className="text-sm font-semibold text-gray-800">
              Attribute Table
             </h3>
            <span>▼</span>
          </div>

          {/* Counter */}
          <div className="px-3 py-1 bg-gray-50 border-b border-[#DADFE7]">
            <span className="text-xs text-gray-600">
              {processedRows.length} elements
            </span>
          </div>
          
          {/* Loading in progress */}
          {loading && (
            <div className="p-4 text-sm text-gray-500">
              Loading attribute table…
            </div>
          )}
          {/* Error handling */}
          {error && (
            <div className="p-4 text-sm text-red-600">
              {error}
            </div>
          )}

          {/* TABLE */}
          <div className="flex-1 overflow-x-auto overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-100 sticky top-0">
                <tr>
                  
                  {data?.headers.map((h) => (
                    <th
                      key={h.name}
                      onClick={() => h.sortable && handleSort(h.name)}
                      className="p-2 text-left cursor-pointer hover:bg-gray-200 border-b border-[#DADFE7]"
                    >
                      {h.name}
                      {sortConfig?.key === h.name && (
                        <span className="ml-1 text-xs">
                          {sortConfig.direction === "asc" ? "↑" : "↓"}
                        </span>
                      )}
                    </th>
                  ))}
                </tr>
              </thead>

              <tbody>
                {processedRows.length === 0 ? (
                  <tr>
                    <td
                      colSpan={(data?.headers.length ?? 0) + 1}
                      className="p-4 text-center text-sm text-gray-500"
                    >
                      No layer selected or data available.
                    </td>
                  </tr>
                ) : (
                  processedRows.map((row, idx) => (
                    <tr
                      key={idx}
                      
                    >
                      
                      {data?.headers.map((h) => (
                        <td
                          key={h.name}
                          className="p-2 border-b border-[#DADFE7]"
                        >
                          {String(row[h.name] ?? "")}
                        </td>
                      ))}
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AttributeTable;
