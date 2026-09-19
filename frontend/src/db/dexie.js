import Dexie from 'dexie';

export const db = new Dexie('KiranaVoiceDB');

db.version(1).stores({
  products_cache: 'id, name, current_stock, base_unit, selling_price',
  pending_txns: 'client_txn_id, product_id, type, quantity, unit, status, attempts, created_at'
});