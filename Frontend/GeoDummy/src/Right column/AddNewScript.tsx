import { useEffect, useState, useRef } from "react";
import { FolderOpen, Plus, X } from "lucide-react";
import WindowTemplate from "../TemplateModals/PopUpWindowModal";
import { colors, typography, radii, spacing, icons, shadows } from "../Design/DesignTokens";
import { ThreeDot } from "react-loading-indicators"

type AddNewScriptProps = {
    onClose: () => void;
    onAddScript: (name: string, category: string, description: string) => void;
    existingCategories: string[];
};
type SaveStatus = "unsaved" | "saving" | "saved";
type Layer = {
    id: string;
    type: "raster" | "vetorial" | "both";
};
type Parameter = { name: string; type: string };

export default function AddNewScript({ onClose, onAddScript, existingCategories }: AddNewScriptProps) {
    const [selectedFileName, setSelectedFileName] = useState<string | null>(null);
    const [category, setCategory] = useState("");
    const [name, setName] = useState("");
    const [error, setError] = useState<string | null>(null);
    const [paramsOpen, setParamsOpen] = useState(false);
    
    const [layers, setLayers] = useState<Layer[]>([]);
    const [description, setDescription] = useState("");
    const [params, setParams] = useState<Parameter[]>([]);
    const [isUploading, setIsUploading] = useState(false);
    const [saveStatus, setSaveStatus] = useState<SaveStatus>("unsaved");
    const [scriptFile, setScriptFile] = useState<File | null>(null);
    
    const [showAddMenu, setShowAddMenu] = useState(false);
    const addMenuRef = useRef<HTMLDivElement | null>(null);
    const [showLayerTypeDropdown, setShowLayerTypeDropdown] = useState<string | null>(null);
    const [showDropdown, setShowDropdown] = useState(false);

    // Backend Communication
    /*async function postScript(
        file: File,
        metadata: {
            name: string;
            category: string;
            description: string;
            layer_type: string;
            parameters: Array<{ name: string; type: string }>;
        }
        ) {
        const formData = new FormData();

        formData.append("file", file);
        formData.append("metadata", JSON.stringify(metadata));

        const res = await fetch("http://localhost:5050/scripts", {
            method: "POST",
            body: formData,
        });

        if (!res.ok) {
            throw new Error("Error saving script");
        }

        return res.json();
    }*/

    
    useEffect(() => {
        // reset when opened (component is mounted each time in current usage)
        setSelectedFileName(null);
        setCategory("");
        setName("");
        setError(null);
        setParamsOpen(false);
       
        setLayers([]);
        setDescription("");
        setParams([]);
        setSaveStatus("unsaved");
        setShowAddMenu(false);
        setShowLayerTypeDropdown(null);
    }, []);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        const isPythonFile =
            file.name.toLowerCase().endsWith(".py") ||
            file.type === "text/x-python";

        if (!isPythonFile) {
            setError("Only .py files are allowed.");
            e.target.value = ""; // reset input
            setSelectedFileName(null);
            return;
        }

        setError(null);
        setSelectedFileName(file.name);
        setScriptFile(file);
        setSaveStatus("unsaved");
    };

    const handleUpload = async () => {
        // Basic validation
        if (!scriptFile) {
            setError("Please choose a script file.");
            return;
        }
        if (!name || !category){
            setError("Please fill in all required fields.");
            return;
        }

        setIsUploading(true);
        setSaveStatus("saving");
        setError(null);
        const metadata = {
            name,
            category,
            description,
            layers: layers.map(l => l.type),
            parameters: params.filter(p => p.name && p.type),
        };
        try{
            await postScriptMock(scriptFile, metadata);
            setSaveStatus("saved");
            onAddScript(name, category, description);
            setTimeout(onClose, 500);
        } catch (err) {
            console.error("Upload error:", err);
            setError("Failed to upload script. Please try again.");
            setSaveStatus("unsaved");
           
        }finally{
            setIsUploading(false);
        }
        /*await new Promise((resolve) => setTimeout(resolve, 1200));

        const paramsString = params.length
            ? `\nParams: ${params
                .filter((p) => p.name || p.type)
                .map((p) => `${p.name || "?"}:${p.type || "?"}`)
                .join(", ")}`
            : "";
        const descriptionWithParams = `${description}${paramsString}`;

        // Call parent handler with the form data
        onAddScript(name, category, descriptionWithParams);
        
        setSaveStatus("saved");
        setIsUploading(false);
        setTimeout(() => {
            onClose();
        }, 600);*/
    };

    // Mock function to simulate backend upload
    async function postScriptMock(
        file: File,
        metadata: {
            name: string;
            category: string;
            description: string;
            layers: string[];
            parameters: Parameter[];
        }
        ) {
        console.log("📦 Mock upload script");
        console.log("File:", file);
        console.log("Metadata:", metadata);

        // simula latência de rede
        await new Promise((r) => setTimeout(r, 800));

        // simula resposta do backend
        return {
            id: crypto.randomUUID(),
            name: metadata.name,
            created_at: new Date().toISOString(),
        };
    }

    const filteredCategories = existingCategories.filter((cat) =>
        cat.toLowerCase().includes(category.toLowerCase())
        );

    const wrapperRef = useRef<HTMLDivElement | null>(null);
    const layerTypeWrapperRef = useRef<HTMLDivElement | null>(null);

    // Handlers para adicionar layers e parâmetros
    const handleAddLayer = () => {
        const newLayer: Layer = {
            id: crypto.randomUUID(),
            type: "" as "raster" | "vetorial" | "both",
        };
        setLayers([...layers, newLayer]);
        setSaveStatus("unsaved");
        setShowAddMenu(false);
    };

    const handleAddParam = () => {
        setParams([...params, { name: "", type: "" }]);
        setSaveStatus("unsaved");
        setShowAddMenu(false);
    };

    const handleRemoveLayer = (id: string) => {
        setLayers(layers.filter(l => l.id !== id));
        setSaveStatus("unsaved");
    };

    const handleLayerTypeChange = (id: string, newType: "raster" | "vetorial" | "both") => {
        setLayers(layers.map(l => l.id === id ? { ...l, type: newType } : l));
        setSaveStatus("unsaved");
        setShowLayerTypeDropdown(null);
    };

    useEffect(() => {
        function handleClickOutside(e: MouseEvent) {
            if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
                setShowDropdown(false);
            }
            if (layerTypeWrapperRef.current && !layerTypeWrapperRef.current.contains(e.target as Node)) {
                setShowLayerTypeDropdown(null);
            }
            if (addMenuRef.current && !addMenuRef.current.contains(e.target as Node)) {
                setShowAddMenu(false);
            }
        }

        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    return (
        <WindowTemplate isOpen={true} onClose={onClose} title="Add New Script">
            <div
                style={{
                    display: "flex",
                    flexDirection: "column",
                    rowGap: spacing.lg,
                }}
            >
                <div style={{ display: "flex", alignItems: "center", columnGap: 16 }}>
                        <label
                            style={{
                                width: 120,
                                fontSize: typography.sizeSm,
                                fontWeight: 600,
                                color: colors.foreground,
                                fontFamily: typography.normalFont,
                            }}
                        >
                            Script Name
                        </label>
                        <div style={{ flex: 1 }}>
                            <input
                                value={name}
                                onChange={(e) => {setName(e.target.value);
                                            setSaveStatus("unsaved");
                                }}
                                placeholder="e.g. Tree Height Analyzer"
                                style={{
                                    width: "100%",
                                    paddingInline: 12,
                                    paddingBlock: 8,
                                    borderRadius: radii.md,
                                    borderStyle: "solid",
                                    borderWidth: 1,
                                    backgroundColor: colors.borderStroke,
                                    borderColor: colors.borderStroke,
                                    outline: "none",
                                    fontSize: typography.sizeSm,
                                    fontFamily: typography.normalFont,
                                }}
                            />
                        </div>
                    </div>
                {/* Choose Script File */}
                <div
                    style={{
                        display: "flex",
                        alignItems: "center",
                        columnGap: 16,
                    }}
                >
                    <label
                        style={{
                            width: 120,
                            fontSize: typography.sizeSm,
                            fontWeight: 600,
                            color: colors.foreground,
                            fontFamily: typography.normalFont,
                        }}
                    >
                        Choose Script File
                    </label>

                    <div style={{ flex: 1 }}>
                        <label
                            style={{
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "space-between",
                                paddingInline: 12,
                                paddingBlock: 8,
                                borderRadius: radii.md,
                                fontSize: typography.sizeSm,
                                cursor: "pointer",
                                borderStyle: "solid",
                                borderWidth: 1,
                                backgroundColor: colors.borderStroke,
                                color: colors.foreground,
                                borderColor: colors.borderStroke,
                                fontFamily: typography.normalFont,
                            }}
                        >
                            <span>{selectedFileName ?? "Browse Files"}</span>
                            <FolderOpen size={icons.size} strokeWidth={icons.strokeWidth} />

                            <input
                                type="file"
                                accept=".py"
                                onChange={handleFileChange}
                                style={{ display: "none" }}
                            />
                        </label>
                    </div>
                </div>
                
                    <div style={{ display: "flex", alignItems: "center", columnGap: 16, position: "relative" }}>
                        <label
                            style={{
                            width: 120,
                            fontSize: typography.sizeSm,
                            fontWeight: 600,
                            color: colors.foreground,
                            fontFamily: typography.normalFont,
                            }}
                        >
                            Category
                        </label>

                        <div ref={wrapperRef} style={{ flex: 1, position: "relative" }}>

                            <input
                            value={category}
                            onChange={(e) => {setCategory(e.target.value); setSaveStatus("unsaved");}}
                            placeholder="e.g. Analysis"
                            onFocus={() => setShowDropdown(true)}
                            style={{
                                width: "100%",
                                paddingInline: 12,
                                paddingBlock: 8,
                                borderRadius: radii.md,
                                borderStyle: "solid",
                                borderWidth: 1,
                                backgroundColor: colors.borderStroke,
                                borderColor: colors.borderStroke,
                                outline: "none",
                                fontSize: typography.sizeSm,
                                fontFamily: typography.normalFont,
                                
                            }}
                            />

                            {/* Dropdown */}
                            {showDropdown && filteredCategories.length > 0 && (
                            <div
                                style={{
                                        position: "absolute",
                                        top: "100%",
                                        left: 0,
                                        right: 0,
                                        marginTop: 4,
                                        maxHeight: 200,
                                        overflowY: "auto",
                                        borderRadius: radii.md,
                                        borderStyle: "solid",
                                        borderWidth: 1,
                                        backgroundColor: colors.cardBackground,
                                        borderColor: colors.borderStroke,
                                        fontSize: typography.sizeSm,
                                        fontFamily: typography.normalFont,
                                        color: colors.foreground,
                                        boxShadow: shadows.subtle,
                                        zIndex: 1000,
                                    }}
                            >
                                {filteredCategories.map((cat) => (
                                <div
                                    key={cat}
                                    onClick={() => {
                                    setCategory(cat);
                                    setShowDropdown(false);
                                    }}
                                    onMouseEnter={(e) => {
                                        e.currentTarget.style.backgroundColor = colors.borderStroke;
                                    }}
                                    onMouseLeave={(e) => {
                                        e.currentTarget.style.backgroundColor = "transparent";
                                    }}
                                    style={{
                                    paddingInline: 12,
                                    paddingBlock: 8,
                                    cursor: "pointer",
                                    fontFamily: typography.normalFont,
                                    transition: "background-color 0.15s ease",
                                    }}
                                >
                                    {cat}
                                </div>
                                ))}
                            </div>
                            )}
                        </div>
                    </div>

                    <div style={{ display: "flex", alignItems: "center", columnGap: 16 }}>
                        <label
                            style={{
                                width: 120,
                                fontSize: typography.sizeSm,
                                fontWeight: 600,
                                color: colors.foreground,
                                fontFamily: typography.normalFont,
                            }}
                        >
                            Description
                        </label>
                        <div style={{ flex: 1 }}>
                            <input
                                value={description}
                                onChange={(e) => setDescription(e.target.value)}
                                placeholder="e.g. A tool to analyze tree heights"
                                style={{
                                    width: "100%",
                                    paddingInline: 12,
                                    paddingBlock: 8,
                                    borderRadius: radii.md,
                                    borderStyle: "solid",
                                    borderWidth: 1,
                                    backgroundColor: colors.borderStroke,
                                    borderColor: colors.borderStroke,
                                    outline: "none",
                                    fontSize: typography.sizeSm,
                                    fontFamily: typography.normalFont,
                                }}
                            />
                        </div>
                    </div>
                {/* Parameters and Layers Toggle */}
                <div style={{ borderBottom: `1px solid ${colors.borderStroke}` }}>
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                        <h4 style={{ margin: 0, fontSize: typography.sizeMd, fontWeight: 600, color: colors.foreground, fontFamily: typography.normalFont }}>Parameters</h4>

                        <div ref={addMenuRef} style={{ position: "relative" }}>
                            <Plus
                                size={20}
                                onClick={() => setShowAddMenu(!showAddMenu)}
                                style={{ cursor: "pointer", color: colors.foreground }}
                            />
                            {showAddMenu && (
                                <div
                                    style={{
                                        position: "absolute",
                                        top: "100%",
                                        right: 0,
                                        marginTop: 8,
                                        borderRadius: radii.md,
                                        borderStyle: "solid",
                                        borderWidth: 1,
                                        backgroundColor: colors.cardBackground,
                                        borderColor: colors.borderStroke,
                                        fontSize: typography.sizeSm,
                                        fontFamily: typography.normalFont,
                                        color: colors.foreground,
                                        boxShadow: shadows.subtle,
                                        zIndex: 1001,
                                        minWidth: 150,
                                    }}
                                >
                                    <div
                                        onClick={handleAddLayer}
                                        onMouseEnter={(e) => {
                                            e.currentTarget.style.backgroundColor = colors.borderStroke;
                                        }}
                                        onMouseLeave={(e) => {
                                            e.currentTarget.style.backgroundColor = "transparent";
                                        }}
                                        style={{
                                            paddingInline: 12,
                                            paddingBlock: 8,
                                            cursor: "pointer",
                                            transition: "background-color 0.15s ease",
                                        }}
                                    >
                                        Add Layer
                                    </div>
                                    <div
                                        onClick={handleAddParam}
                                        onMouseEnter={(e) => {
                                            e.currentTarget.style.backgroundColor = colors.borderStroke;
                                        }}
                                        onMouseLeave={(e) => {
                                            e.currentTarget.style.backgroundColor = "transparent";
                                        }}
                                        style={{
                                            paddingInline: 12,
                                            paddingBlock: 8,
                                            cursor: "pointer",
                                            borderTop: `1px solid ${colors.borderStroke}`,
                                            transition: "background-color 0.15s ease",
                                        }}
                                    >
                                        Add Parameter
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                    
                    {(params.length > 0 || layers.length > 0 || paramsOpen) && (
                        <div style={{ padding: `${spacing.md} 0`, display: "flex", flexDirection: "column", gap: spacing.sm }}>
                            {/* Layers Section */}
                            {layers.length > 0 && (
                                <div style={{ display: "flex", flexDirection: "column", gap: spacing.sm, paddingBottom: spacing.sm, borderBottom: `1px solid ${colors.borderStroke}` }}>
                                    <p style={{ margin: 0, fontSize: typography.sizeSm, fontWeight: 600, color: colors.foreground, fontFamily: typography.normalFont }}>Layers</p>
                                    {layers.map((layer) => (
                                        <div key={layer.id} style={{ display: "flex", alignItems: "center", columnGap: 8 }}>
                                            <div ref={layerTypeWrapperRef} style={{ flex: 1, position: "relative" }}>
                                                <input
                                                    value={layer.type === "raster" ? "Raster" : layer.type === "vetorial" ? "Vetorial" : layer.type === "both" ? "Both" : ""}
                                                    readOnly
                                                    placeholder="Select Layer Type"
                                                    onClick={() => setShowLayerTypeDropdown(showLayerTypeDropdown === layer.id ? null : layer.id)}
                                                    
                                                    style={{
                                                        width: "100%",
                                                        paddingInline: 12,
                                                        paddingBlock: 8,
                                                        borderRadius: radii.md,
                                                        borderStyle: "solid",
                                                        borderWidth: 1,
                                                        backgroundColor: colors.borderStroke,
                                                        borderColor: colors.borderStroke,
                                                        outline: "none",
                                                        fontSize: typography.sizeSm,
                                                        fontFamily: typography.normalFont,
                                                        color: colors.foreground,
                                                        cursor: "pointer",
                                                    }}
                                                />
                                                {showLayerTypeDropdown === layer.id && (
                                                    <div
                                                        style={{
                                                            position: "absolute",
                                                            top: "100%",
                                                            left: 0,
                                                            right: 0,
                                                            marginTop: 4,
                                                            borderRadius: radii.md,
                                                            borderStyle: "solid",
                                                            borderWidth: 1,
                                                            backgroundColor: colors.cardBackground,
                                                            borderColor: colors.borderStroke,
                                                            fontSize: typography.sizeSm,
                                                            fontFamily: typography.normalFont,
                                                            color: colors.foreground,
                                                            boxShadow: shadows.subtle,
                                                            zIndex: 1000,
                                                        }}
                                                    >
                                                        {[
                                                            { value: "raster", label: "Raster" },
                                                            { value: "vetorial", label: "Vetorial" },
                                                            { value: "both", label: "Ambos" },
                                                        ].map((option) => (
                                                            <div
                                                                key={option.value}
                                                                onClick={() => handleLayerTypeChange(layer.id, option.value as "raster" | "vetorial" | "both")}
                                                                onMouseEnter={(e) => {
                                                                    e.currentTarget.style.backgroundColor = colors.borderStroke;
                                                                }}
                                                                onMouseLeave={(e) => {
                                                                    e.currentTarget.style.backgroundColor = "transparent";
                                                                }}
                                                                style={{
                                                                    paddingInline: 12,
                                                                    paddingBlock: 8,
                                                                    cursor: "pointer",
                                                                    fontFamily: typography.normalFont,
                                                                    transition: "background-color 0.15s ease",
                                                                }}
                                                            >
                                                                {option.label}
                                                            </div>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                            <button
                                                onClick={() => handleRemoveLayer(layer.id)}
                                                style={{
                                                    padding: 8,
                                                    backgroundColor: "transparent",
                                                    border: "none",
                                                    cursor: "pointer",
                                                    color: colors.error,
                                                    display: "flex",
                                                    alignItems: "center",
                                                    justifyContent: "center",
                                                }}
                                            >
                                                <X size={18} />
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            )}
                            
                            {/* Parameters Section */}
                            {params.length > 0 && (
                                <div style={{ display: "flex", flexDirection: "column", gap: spacing.sm, paddingBottom: spacing.sm, borderBottom: `1px solid ${colors.borderStroke}` }}>
                                    <p style={{ margin: 0, fontSize: typography.sizeSm, fontWeight: 600, color: colors.foreground, fontFamily: typography.normalFont }}>Common Parameters</p>
                                    {params.map((p, idx) => (
                                        <div key={idx} style={{ display: "flex", columnGap: spacing.md }}>
                                            <input
                                                value={p.name}
                                                onChange={(e) => {
                                                    const value = e.target.value;
                                                    setParams((prev) => prev.map((item, i) => i === idx ? { ...item, name: value } : item));
                                                    setSaveStatus("unsaved");
                                                }}
                                                placeholder="Parameter name"
                                                style={{
                                                    flex: 1,
                                                    paddingInline: 12,
                                                    paddingBlock: 8,
                                                    borderRadius: radii.md,
                                                    borderStyle: "solid",
                                                    borderWidth: 1,
                                                    backgroundColor: colors.borderStroke,
                                                    borderColor: colors.borderStroke,
                                                    outline: "none",
                                                    fontSize: typography.sizeSm,
                                                    fontFamily: typography.normalFont,
                                                    color: colors.foreground,
                                                }}
                                            />
                                            <select
                                                value={p.type}
                                                onChange={(e) => {
                                                    const value = e.target.value;
                                                    setParams((prev) => prev.map((item, i) => i === idx ? { ...item, type: value } : item));
                                                    setSaveStatus("unsaved");
                                                }}
                                                style={{
                                                    flexBasis: "40%",
                                                    paddingInline: 12,
                                                    paddingBlock: 8,
                                                    borderRadius: radii.md,
                                                    borderStyle: "solid",
                                                    borderWidth: 1,
                                                    backgroundColor: colors.cardBackground,
                                                    borderColor: colors.borderStroke,
                                                    outline: "none",
                                                    fontSize: typography.sizeSm,
                                                    fontFamily: typography.normalFont,
                                                    color: colors.foreground,
                                                    cursor: "pointer",
                                                }}
                                            >
                                                <option value="">Type</option>
                                                <option value="int">int</option>
                                                <option value="float">float</option>
                                                <option value="bool">bool</option>
                                                <option value="string">string</option>
                                                <option value="number">number</option>
                                            </select>
                                            <button
                                                onClick={() => {
                                                    setParams(params.filter((_, i) => i !== idx));
                                                    setSaveStatus("unsaved");
                                                }}
                                                style={{
                                                    padding: 8,
                                                    backgroundColor: "transparent",
                                                    border: "none",
                                                    cursor: "pointer",
                                                    color: colors.error,
                                                    display: "flex",
                                                    alignItems: "center",
                                                    justifyContent: "center",
                                                }}
                                            >
                                                <X size={18} />
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}
                </div>

                {/* Error */}
                {error && (
                    <p style={{ margin: 0, color: colors.error, fontFamily: typography.normalFont }}>
                        {error}
                    </p>
                )}

                <div
                    style={{
                        padding: "6px 12px",
                        borderRadius: radii.sm,
                        fontSize: typography.sizeSm,
                        fontFamily: typography.normalFont,
                        alignSelf: "flex-start",
                        color:
                            saveStatus === "saved"
                                ? colors.accent
                                :saveStatus === "saving"
                                ? colors.primary
                                : colors.error,
                        
                    }}
                >
                    {saveStatus === "saving" ? "Saving..." : saveStatus === "saved" ? "Saved" : "Not saved"}
                </div>

                {/* Footer actions */}
                <div style={{ display: "flex", justifyContent: "flex-end", marginTop: spacing.md }}>
                    <button
                        onClick={handleUpload}
                        disabled={isUploading}
                        style={{
                            backgroundColor: isUploading ? colors.borderStroke : colors.primary,
                            color: colors.primaryForeground,
                            opacity: isUploading ? 0.7 : 1,
                            cursor: isUploading ? "not-allowed" : "pointer",
                            fontFamily: typography.normalFont,
                            paddingInline: spacing.lg,
                            paddingBlock: spacing.sm,
                            borderRadius: radii.md,
                            border: "none",
                            fontSize: typography.sizeSm,
                            fontWeight: 500,
                        }}
                    >
                        {isUploading ? (<ThreeDot
                            color="#ffffff"
                            size="small"
                            text=""
                            textColor=""
                            />) : "Upload"}
                        
                    </button>
                </div>
            </div>
        </WindowTemplate>
    );
}