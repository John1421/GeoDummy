function EditMenu({ open }: { open: boolean }) {
  if (!open) return null;

  return (
    <div className="absolute top-full left-0 mt-2 bg-white border border-gray-200 rounded-lg shadow-lg w-40 z-50">
      <button className="w-full text-black text-left px-4 py-2 hover:bg-gray-100">
        Edit Base Map
      </button>
      <button className="w-full text-black text-left px-4 py-2 hover:bg-gray-100">
        Settings
      </button>
    </div>
  );
}

export default EditMenu;
