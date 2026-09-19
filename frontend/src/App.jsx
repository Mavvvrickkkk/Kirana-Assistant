import { useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import axios from 'axios';
import { db } from './db/dexie';
import Dashboard from './pages/Dashboard';
import VoiceAssistant from './pages/VoiceAssistant';
import Inventory from './pages/Inventory';
import History from './pages/History';
import Settings from './pages/Settings';
import Navigation from './components/Navigation';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export default function App() {
  useEffect(() => {
    const syncOffline = async () => {
      if (!navigator.onLine) return;
      
      // 1. Sync pending txns
      const items = await db.pending_txns.toArray();
      if (items.length > 0) {
        try {
          const res = await axios.post(`${API_BASE}/inventory/sync/transactions`, { transactions: items });
          for (const itemResult of res.data) {
            // Preserve errors; only delete SUCCESS or DUPLICATE
            if (itemResult.status === 'SUCCESS' || itemResult.status === 'DUPLICATE') {
              await db.pending_txns.where('client_txn_id').equals(itemResult.client_txn_id).delete();
            }
          }
        } catch (e) {
          console.error("Sync failed", e);
        }
      }
      
      // 2. Refresh product cache for offline viewing
      try {
        const res = await axios.get(`${API_BASE}/inventory`);
        await db.products_cache.clear();
        await db.products_cache.bulkAdd(res.data);
      } catch (e) {
        console.error("Failed to update cache", e);
      }
    };

    window.addEventListener('online', syncOffline);
    if (navigator.onLine) syncOffline();

    return () => window.removeEventListener('online', syncOffline);
  }, []);

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50 flex flex-col">
        <Navigation />
        <main className="flex-grow container mx-auto p-4 md:p-6 mb-20 md:mb-0">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/assistant" element={<VoiceAssistant />} />
            <Route path="/inventory" element={<Inventory />} />
            <Route path="/history" element={<History />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}