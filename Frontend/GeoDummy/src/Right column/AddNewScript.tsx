import { useEffect, useState, useRef } from "react";
import { FolderOpen, Plus } from "lucide-react";
import WindowTemplate from "../TemplateModals/PopUpWindowModal";
import { colors, typography, radii, spacing, icons } from "../Design/DesignTokens";
import { ThreeDot } from "react-loading-indicators"

type AddNewScriptProps = {
    onClose: () => void;
    onAddScript: (name: string, category: string, description: string) => void;
    existingCategories: string[];
};
type SaveStatus = "unsaved" | "saving" | "saved";

export default function AddNewScript({ onClose, onAddScript, existingCategories }: AddNewScriptProps) {
    const [selectedFileName, setSelectedFileName] = useState<string | null>(null);
    const [category, setCategory] = useState("");
    const [name, setName] = useState("");
    const [error, setError] = useState<string | null>(null);
    const [paramsOpen, setParamsOpen] = useState(false);
    const [selectedParams, setSelectedParams] = useState<string[]>([]);
    const [layerType, setLayerType] = useState<string>("");
    const [description, setDescription] = useState("");
    const [isUploading, setIsUploading] = useState(false);
    const [saveStatus, setSaveStatus] = useState<SaveStatus>("unsaved");

    useEffect(() => {
        // reset when opened (component is mounted each time in current usage)
        setSelectedFileName(null);
        setCategory("");
        setName("");
        setError(null);
        setParamsOpen(false);
        setSelectedParams([]);
        setLayerType("");
        setDescription("");
        setSaveStatus("unsaved");
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
        setSaveStatus("unsaved");
    };


    const handleParamToggle = (paramType: string) => {
        setSelectedParams((prev) =>
            prev.includes(paramType) ? [] : [paramType]
        );
    };

    const handleUpload = async () => {
        // Basic validation
        if (!selectedFileName) {
            setError("Please choose a script file.");
            return;
        }
        setIsUploading(true);
        setSaveStatus("saving");
        await new Promise((resolve) => setTimeout(resolve, 1200));
        // Call parent handler with the form data
        onAddScript(name, category, description);
        
        setSaveStatus("saved");
        setIsUploading(false);
        setTimeout(() => {
            onClose();
        }, 600);
    };
    const [showDropdown, setShowDropdown] = useState(false);

    const filteredCategories = existingCategories.filter((cat) =>
        cat.toLowerCase().includes(category.toLowerCase())
        );

    const wrapperRef = useRef<HTMLDivElement | null>(null);
    useEffect(() => {
        function handleClickOutside(e: MouseEvent) {
            if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
                setShowDropdown(false);
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
                            >
                                {filteredCategories.map((cat) => (
                                <div
                                    key={cat}
                                    onClick={() => {
                                    setCategory(cat);
                                    setShowDropdown(false);
                                    }}
                                    style={{
                                    padding: "8px 12px",
                                    cursor: "pointer",
                                    fontFamily: typography.normalFont,
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
                {/* Parameters Toggle */}
                <div style={{ borderBottom: `1px solid ${colors.borderStroke}` }}>
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                        <h4 style={{ margin: 0, fontSize: typography.sizeMd, fontWeight: 600, color: colors.foreground, fontFamily: typography.normalFont }}>Parameters</h4>

                        <Plus
                            size={20}
                            onClick={() => setParamsOpen(!paramsOpen)}
                            style={{ cursor: "pointer", color: colors.foreground }}
                        />
                    </div>

                    {paramsOpen && (
                        <div style={{ padding: `${spacing.md} 0`, display: "flex", flexDirection: "column", gap: spacing.sm }}>
                            <button
                                onClick={() => handleParamToggle("number")}
                                style={{
                                    padding: `${spacing.sm} ${spacing.md}`,
                                    backgroundColor: selectedParams.includes("number") ? colors.primary : colors.cardBackground,
                                    color: selectedParams.includes("number") ? colors.primaryForeground : colors.foreground,
                                    border: `1px solid ${colors.borderStroke}`,
                                    borderRadius: radii.md,
                                    fontSize: typography.sizeSm,
                                    fontFamily: typography.normalFont,
                                    cursor: "pointer",
                                }}
                            >
                                Number
                            </button>

                            <div style={{ display: "flex", flexDirection: "column", gap: spacing.sm }}>
                                <label
                                    style={{
                                        fontSize: typography.sizeSm,
                                        fontWeight: 600,
                                        color: colors.foreground,
                                        fontFamily: typography.normalFont,
                                    }}
                                >
                                    Layer Type
                                </label>
                                <select
                                    value={layerType}
                                    onChange={(e) => {
                                        setLayerType(e.target.value);
                                        setSaveStatus("unsaved");
                                    }}
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
                                >
                                    <option value="">Select layer type...</option>
                                    <option value="raster">Raster</option>
                                    <option value="vetorial">Vetorial</option>
                                    <option value="both">Ambos</option>
                                </select>
                            </div>
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