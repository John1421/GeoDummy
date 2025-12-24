import React, { useState } from 'react';
import PopUpWindowModal from '../TemplateModals/PopUpWindowModal';
import { Play, FolderOpen } from "lucide-react";


interface RunScriptWindowProps {
  isOpen: boolean;
  onClose: () => void;
  scriptId: string;
  onRunScript: (
    scriptId: string,
    inputFilePath: string,
    numberValue: number,
    listValue: number[]
  ) => void;
}

const RunScriptWindow: React.FC<RunScriptWindowProps> = ({ isOpen, onClose, scriptId, onRunScript }) => {
  const [inputFilePath, setInputFilePath] = useState<string | null>(null);
  const [numberValue, setNumberValue] = useState<number>(0);
  const [listValue, setListValue] = useState<string>(''); // Store as string, parse on submit

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setInputFilePath(file.name);
  };

  const handleRunScript = () => {
    // For now, listValue is a string, and we'll just split it by commas.
    // In a real application, you might want more robust parsing and error handling.
    const parsedList = listValue.split(',').map(item => parseInt(item.trim())).filter(item => !isNaN(item));
    onRunScript(scriptId, inputFilePath || '', numberValue, parsedList);
    onClose();
  };

  return (
    <PopUpWindowModal
      title="Execute Script"
      isOpen={isOpen}
      onClose={onClose}
    >
      <div className="flex flex-col p-4 space-y-4">
        <div className="flex items-center space-x-4">
          <label htmlFor="file-input" className="w-20 text-sm font-medium text-gray-700">Input</label>
          <div className="flex-1">
            <label
              htmlFor="file-input"
              className="flex items-center justify-between px-3 py-2 border border-gray-300 rounded-md text-sm cursor-pointer bg-[#DADFE7] text-gray-700"
            >
              <span>{inputFilePath ?? "Browse Files"}</span>
              <FolderOpen size={18} />
              <input
                type="file"
                id="file-input"
                onChange={handleFileChange}
                className="hidden"
              />
            </label>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          <label htmlFor="output-display" className="w-20 text-sm font-medium text-gray-700">Output</label>
          <div id="output-display" className="flex-1 p-2 h-10 border border-gray-300 rounded-md bg-[#DADFE7] flex items-center text-sm text-gray-500">
          </div>
        </div>

        <h3 className="text-lg font-semibold text-gray-800 pb-2 mb-2">Parameters</h3>

        <div className="flex flex-col space-y-2">
          <div className="flex items-center space-x-2">
            <label htmlFor="number-input" className="w-20 text-sm font-medium text-gray-700">Number</label>
            <input
              type="number"
              id="number-input"
              value={numberValue}
              onChange={(e) => setNumberValue(parseInt(e.target.value))}
              className="ml-40 flex-grow p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 bg-[#DADFE7] focus:ring-blue-500"
            />
          </div>

          <div className="flex items-center space-x-2">
            <label htmlFor="list-input" className="w-20 text-sm font-medium text-gray-700">List</label>
            <div className="flex-grow flex items-center relative">
              <input
                type="text"
                id="list-input"
                value={listValue}
                onChange={(e) => setListValue(e.target.value)}
                className="ml-40 w-full  p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 bg-[#DADFE7] focus:ring-blue-500 pr-8"
                placeholder="e.g., 1, 2, 3"
              />
              <Play size={16} className="absolute right-2 text-gray-500" />
            </div>
          </div>
        </div>

        <button
          onClick={handleRunScript}
          className="mt-4 flex items-center justify-center py-2 px-4 bg-[#0D73A5] text-white font-semibold rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors duration-200"
        >
          <Play size={16} className="mr-2" />
          Run Script
        </button>
      </div>
    </PopUpWindowModal>
  );
};

export default RunScriptWindow;
