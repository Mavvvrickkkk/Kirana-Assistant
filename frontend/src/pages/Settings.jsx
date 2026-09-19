import { useState, useEffect } from 'react';
import { db } from '../db/dexie';
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export default function Settings() {
  const [pendingTxns, setPendingTxns] = useState([]);

  const refreshOfflineQueue = async () => {
    const items = await db.pending_txns.toArray();
    setPendingTxns(items);
  };

  useEffect(() => {
    refreshOfflineQueue();
  }, []);

  const triggerSync = async () => {
    const items = await db.pending_txns.toArray();
    if (items.length === 0) return;

    try {
      const res = await axios.post(`${API_BASE}/inventory/sync/transactions`, { transactions: items });
      for (const itemResult of res.data) {
        if (itemResult.status === 'SUCCESS' || itemResult.status === 'DUPLICATE') {
          await db.pending_txns.where('client_txn_id').equals(itemResult.client_txn_id).delete();
        }
      }
      refreshOfflineQueue();
      alert("Sync completed.");
    } catch (e) {
      alert("Sync failed: " + e.message);
    }
  };

  return (
    <div className="space-y-6 max-w-xl">
      <h2 className="text-2xl font-bold text-gray-800">System Settings & Sync</h2>

      <div className="bg-white p-5 rounded-xl border border-gray-100 space-y-4">
        <h3 className="font-bold text-gray-800">Offline Queue Management</h3>
        <p className="text-xs text-gray-500">Pending transactions stored in IndexedDB: {pendingTxns.length}</p>

        <button onClick={triggerSync} className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium">
          Force Sync Now
        </button>

        <div className="divide-y border rounded-lg max-h-48 overflow-y-auto">
          {pendingTxns.map(item => (
            <div key={item.client_txn_id} className="p-2 text-xs flex justify-between">
              <span>{item.type} (Product #{item.product_id})</span>
              <span className="font-bold">{item.quantity} {item.unit}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}