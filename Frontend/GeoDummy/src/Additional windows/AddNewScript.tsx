type AddNewScriptProps = {
	onClose: () => void;
};

function AddNewScript({ onClose }: AddNewScriptProps) {
	return (
		<div
			className="fixed inset-0 flex items-center justify-center"
			style={{ zIndex: 999999 }}
			onClick={onClose}
		>
			<div
				className="bg-white w-130 h-90 rounded shadow-lg p-4"
				onClick={(e) => e.stopPropagation()} /* Prevent closing when clicking inside the modal */
			>
				<div className="flex justify-between items-center mb-2">
					<h3 className="text-lg font-semibold">New Script</h3>
					<button
						aria-label="Close"
						onClick={onClose}
						className="text-xl font-bold leading-none"
					>
						×
					</button>
				</div>
                <div className="mt-4">
                    <div className="flex items-center gap-3">
                        <p>Choose script file</p>
                        <input
                            type="file"
                            className="flex-1 px-1 py-2 bg-gray-200 border border-gray-300 rounded cursor-pointer"
                        />
                    </div>
                </div>
                <div className="mt-4">
                    <h4 className="text-md font-semibold mb-3">Parameters</h4>
                    <div className="flex items-center gap-3 mb-2">
                        <label className="text-sm font-medium w-20">Category</label>
                        <input type="text" className="flex-1 px-2 py-1 bg-gray-200 border border-gray-300 rounded" />
                    </div>
                    <div className="flex items-center gap-3 mb-2">
                        <label className="text-sm font-medium w-20">Number</label>
                        <input type="text" className="flex-1 px-2 py-1 bg-gray-200 border border-gray-300 rounded" />
                    </div>
                    <div className="flex items-center gap-3">
                        <label className="text-sm font-medium w-20">Type</label>
                        <input type="text" className="flex-1 px-2 py-1 bg-gray-200 border border-gray-300 rounded" />
                    </div>
                </div>
                <div className="mt-6 flex justify-end">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
                    >
                        Upload
                    </button>
                </div>

			</div>
		</div>
	);
}

export default AddNewScript;