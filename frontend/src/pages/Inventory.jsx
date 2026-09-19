import { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export default function Inventory() {
  const [products, setProducts] = useState([]);
  const [search, setSearch] = useState('');

  useEffect(() => {
    axios.get(`${API_BASE}/inventory`).then(res => setProducts(res.data)).catch(console.error);
  }, []);

  const filtered = products.filter(p => p.name.toLowerCase().includes(search.toLowerCase()) || (p.name_local && p.name_local.includes(search)));

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-800">Inventory Catalog</h2>
        <input
          type="text"
          placeholder="Search items..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="border rounded-lg px-3 py-1.5 text-sm w-64 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      <div className="bg-white rounded-xl border border-gray-100 overflow-hidden shadow-sm">
        <table className="w-full text-left text-sm">
          <thead className="bg-gray-50 text-gray-500">
            <tr>
              <th className="p-3">ID</th>
              <th className="p-3">Name</th>
              <th className="p-3">Stock</th>
              <th className="p-3">Unit Price</th>
              <th className="p-3">Reorder Level</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {filtered.map(p => (
              <tr key={p.id}>
                <td className="p-3 text-gray-400">{p.id}</td>
                <td className="p-3 font-semibold text-gray-800">{p.name} <span className="text-xs text-gray-400 font-normal">({p.name_local})</span></td>
                <td className="p-3">{p.current_stock} {p.base_unit}</td>
                <td className="p-3">₹{p.selling_price}</td>
                <td className="p-3">{p.reorder_level} {p.base_unit}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}