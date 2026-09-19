import { useState, useEffect } from 'react';
import axios from 'axios';
import { Package, AlertCircle, TrendingUp, DollarSign } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export default function Dashboard() {
  const [products, setProducts] = useState([]);
  const [salesSummary, setSalesSummary] = useState(null);
  const [history, setHistory] = useState([]);

  useEffect(() => {
    axios.get(`${API_BASE}/inventory`).then(res => setProducts(res.data)).catch(console.error);
    axios.get(`${API_BASE}/reports/sales-summary?period=today`).then(res => setSalesSummary(res.data)).catch(console.error);
    axios.get(`${API_BASE}/reports/history`).then(res => setHistory(res.data)).catch(console.error);
  }, []);

  const lowStock = products.filter(p => p.current_stock <= p.reorder_level);
  const totalValue = products.reduce((acc, p) => acc + (p.current_stock * p.selling_price), 0);

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-800">Shop Overview Dashboard</h2>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-xl border border-gray-100 flex items-center gap-4 shadow-sm">
          <div className="p-3 bg-blue-50 text-blue-600 rounded-lg"><Package /></div>
          <div><p className="text-xs text-gray-500 font-medium">Total Products</p><h3 className="text-xl font-bold">{products.length}</h3></div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-gray-100 flex items-center gap-4 shadow-sm">
          <div className="p-3 bg-green-50 text-green-600 rounded-lg"><DollarSign /></div>
          <div><p className="text-xs text-gray-500 font-medium">Total Inventory Value</p><h3 className="text-xl font-bold">₹{totalValue.toFixed(2)}</h3></div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-gray-100 flex items-center gap-4 shadow-sm">
          <div className="p-3 bg-purple-50 text-purple-600 rounded-lg"><TrendingUp /></div>
          <div><p className="text-xs text-gray-500 font-medium">Today's Sales Revenue</p><h3 className="text-xl font-bold">₹{salesSummary?.total_revenue?.toFixed(2) || '0.00'}</h3></div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-red-50 flex items-center gap-4 text-red-600 shadow-sm">
          <div className="p-3 bg-red-50 rounded-lg"><AlertCircle /></div>
          <div><p className="text-xs text-red-500 font-medium">Low Stock Alerts</p><h3 className="text-xl font-bold">{lowStock.length}</h3></div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-100 p-5 space-y-4 shadow-sm">
          <h3 className="font-bold text-gray-800">Low Stock Items</h3>
          <div className="divide-y max-h-60 overflow-y-auto">
            {lowStock.length === 0 ? <p className="text-sm text-gray-400 py-4">All stock levels are healthy.</p> : lowStock.map(p => (
              <div key={p.id} className="py-2.5 flex justify-between items-center text-sm">
                <span className="font-medium text-gray-800">{p.name}</span>
                <span className="px-2.5 py-1 bg-red-100 text-red-700 rounded-full text-xs font-semibold">{p.current_stock} {p.base_unit} left</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-100 p-5 space-y-4 shadow-sm">
          <h3 className="font-bold text-gray-800">Recent Transactions</h3>
          <div className="divide-y max-h-60 overflow-y-auto">
            {history.slice(0, 5).map(m => (
              <div key={m.id} className="py-2.5 flex justify-between items-center text-sm">
                <div>
                  <span className="font-bold text-gray-700">{m.product_name || `Product ${m.product_id}`}</span>
                  <span className="text-xs text-gray-500 ml-2">({m.movement_type})</span>
                  <span className="text-xs text-gray-400 block">{new Date(m.occurred_at).toLocaleTimeString()}</span>
                </div>
                <span className={`font-bold ${m.quantity_delta > 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {m.quantity_delta > 0 ? `+${m.quantity_delta}` : m.quantity_delta}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}