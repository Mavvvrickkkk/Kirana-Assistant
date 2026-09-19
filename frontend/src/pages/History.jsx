import { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export default function History() {
  const [movements, setMovements] = useState([]);

  useEffect(() => {
    axios.get(`${API_BASE}/reports/history`).then(res => setMovements(res.data)).catch(console.error);
  }, []);

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold text-gray-800">Inventory Movement History</h2>
      <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
        <table className="w-full text-left text-sm">
          <thead className="bg-gray-50 text-gray-500">
            <tr>
              <th className="p-3">ID</th>
              <th className="p-3">Product</th>
              <th className="p-3">Type</th>
              <th className="p-3">Delta</th>
              <th className="p-3">Stock After</th>
              <th className="p-3">Timestamp</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {movements.map(m => (
              <tr key={m.id}>
                <td className="p-3 text-gray-400">{m.id}</td>
                <td className="p-3 font-semibold text-gray-800">{m.product_name || `Unknown (${m.product_id})`}</td>
                <td className="p-3 text-gray-600">{m.movement_type}</td>
                <td className={`p-3 font-bold ${m.quantity_delta > 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {m.quantity_delta > 0 ? `+${m.quantity_delta}` : m.quantity_delta}
                </td>
                <td className="p-3">{m.stock_after}</td>
                <td className="p-3 text-xs text-gray-500">{new Date(m.occurred_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}