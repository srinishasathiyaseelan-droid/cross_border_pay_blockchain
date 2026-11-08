import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { CreditCard, Search, RefreshCw, DollarSign, ArrowRightLeft, AlertTriangle, CheckCircle, ShieldCheck, Globe } from 'lucide-react';
import { seedService } from '../services/api';
import { mapBatchToPayment, DEMO_PAYMENTS } from '../constants/paymentData';

const BatchExplorer = () => {
  const [batches, setBatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchId, setSearchId] = useState('');

  // Transfer modal (repurposed as "Release Funds")
  const [showTransfer, setShowTransfer] = useState(false);
  const [transferAddress, setTransferAddress] = useState('');
  const [transferBatchId, setTransferBatchId] = useState(null);

  const [actionLoading, setActionLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState(null);

  useEffect(() => { fetchBatches(); }, []);

  const fetchBatches = async () => {
    setLoading(true);
    try {
      const data = await seedService.getAllBatches();
      setBatches(data);
    } catch (e) {
      console.error('Failed to fetch payments:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async () => {
    if (!searchId.trim()) { fetchBatches(); return; }
    const num = searchId.replace('CP-', '').replace('cp-', '');
    setBatches(batches.filter(b => String(b.batchId) === num));
  };

  const clearSearch = () => {
    setSearchId('');
    fetchBatches();
  };

  const handleTransfer = async (e) => {
    e.preventDefault();
    setActionLoading(true);
    setActionMessage(null);
    try {
      const result = await seedService.transferBatch(transferBatchId, transferAddress);
      setActionMessage({ type: 'success', text: `Funds released! Tx: ${result.txHash?.slice(0, 18)}...` });
      setShowTransfer(false);
      setTransferAddress('');
      fetchBatches();
    } catch (e) {
      setActionMessage({ type: 'error', text: e.response?.data?.error || e.message });
    } finally {
      setActionLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    const styles = {
      'Funded': 'bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300',
      'Completed': 'bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300',
      'Pending': 'bg-yellow-100 dark:bg-yellow-900/40 text-yellow-700 dark:text-yellow-300',
      'In Progress': 'bg-indigo-100 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-300',
      'Refunded': 'bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300',
      'Review': 'bg-orange-100 dark:bg-orange-900/40 text-orange-700 dark:text-orange-300',
    };
    return <span className={`px-3 py-1 text-xs font-bold rounded-full ${styles[status] || styles['Pending']} flex items-center shadow-sm space-x-1`}><span>{status}</span></span>;
  };

  const getRiskBadge = (risk) => {
    const styles = {
      'Low': 'bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300',
      'Medium': 'bg-yellow-100 dark:bg-yellow-900/40 text-yellow-700 dark:text-yellow-300',
      'High': 'bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300',
    };
    return <span className={`px-2 py-0.5 text-xs font-bold rounded-full ${styles[risk] || styles['Low']}`}>{risk}</span>;
  };

  // Map real batches to payment display or use demo data
  const payments = batches.length > 0 
    ? batches.map((b, i) => mapBatchToPayment(b, i))
    : DEMO_PAYMENTS.map((d, i) => ({ ...d, paymentId: d.id, batchId: i + 1 }));

  const filteredPayments = searchId 
    ? payments.filter(p => p.paymentId.toLowerCase().includes(searchId.toLowerCase()) || String(p.batchId) === searchId.replace('CP-', ''))
    : payments;

  return (
    <div className="max-w-6xl mx-auto px-4 py-12 animate-fade-in">
      <div className="mb-10 text-center">
        <h1 className="text-4xl md:text-5xl font-bold bg-gradient-to-r from-indigo-600 to-violet-600 bg-clip-text text-transparent mb-4">Payment Explorer</h1>
        <p className="text-lg text-gray-600 dark:text-gray-300 max-w-2xl mx-auto leading-relaxed">
           Browse cross-border payment records. Verify transactions, track escrow, and manage payment lifecycle.
        </p>
      </div>

      {/* Search Bar */}
      <div className="max-w-3xl mx-auto mb-10 bg-white dark:bg-slate-800 p-2 rounded-2xl shadow-lg border border-gray-100 dark:border-slate-700 flex items-center">
        <div className="flex-1 relative flex items-center">
          <Search className="absolute left-4 h-6 w-6 text-gray-400" />
          <input type="text" value={searchId} onChange={(e) => setSearchId(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="Search by Payment ID (e.g. CP-001)..." className="w-full pl-12 pr-4 py-3 bg-transparent text-gray-900 dark:text-white outline-none font-medium" />
        </div>
        <button onClick={handleSearch} className="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-3 rounded-xl font-bold transition mr-2">Search</button>
        <button onClick={clearSearch} className="p-3 bg-gray-100 dark:bg-slate-700 hover:bg-gray-200 dark:hover:bg-slate-600 rounded-xl transition">
          <RefreshCw className={`h-6 w-6 text-gray-600 dark:text-gray-300 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Action Messages */}
      {actionMessage && (
        <div className={`mb-8 p-4 rounded-xl text-sm flex items-center justify-center space-x-2 max-w-2xl mx-auto shadow-sm ${actionMessage.type === 'success' ? 'bg-green-50 dark:bg-green-900/30 text-green-800 dark:text-green-300 border border-green-200 dark:border-green-800' : 'bg-red-50 dark:bg-red-900/30 text-red-800 dark:text-red-300 border border-red-200 dark:border-red-800'}`}>
          {actionMessage.type === 'success' ? <CheckCircle className="h-5 w-5" /> : <AlertTriangle className="h-5 w-5" />}
          <span className="font-semibold text-base">{actionMessage.text}</span>
        </div>
      )}

      {/* Payment Table */}
      {loading ? (
        <div className="text-center py-20"><RefreshCw className="h-12 w-12 text-indigo-500 animate-spin mx-auto mb-4" /><p className="text-gray-500 font-medium text-lg">Loading payments...</p></div>
      ) : (
        <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-xl border border-gray-100 dark:border-slate-700 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full table-auto">
              <thead>
                <tr className="bg-gray-50 dark:bg-slate-900 text-gray-600 dark:text-gray-300">
                  <th className="px-6 py-4 text-left text-xs font-bold uppercase tracking-wider">Payment ID</th>
                  <th className="px-6 py-4 text-left text-xs font-bold uppercase tracking-wider">Buyer</th>
                  <th className="px-6 py-4 text-left text-xs font-bold uppercase tracking-wider">Supplier</th>
                  <th className="px-6 py-4 text-left text-xs font-bold uppercase tracking-wider">Route</th>
                  <th className="px-6 py-4 text-left text-xs font-bold uppercase tracking-wider">Amount</th>
                  <th className="px-6 py-4 text-left text-xs font-bold uppercase tracking-wider">Status</th>
                  <th className="px-6 py-4 text-left text-xs font-bold uppercase tracking-wider">Risk</th>
                  <th className="px-6 py-4 text-left text-xs font-bold uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-slate-700">
                {filteredPayments.length === 0 ? (
                  <tr><td colSpan={8} className="px-6 py-12 text-center text-gray-400">
                    <CreditCard className="h-12 w-12 mx-auto mb-3 text-gray-300" />
                    <p className="text-lg font-medium">No payments found</p>
                  </td></tr>
                ) : filteredPayments.map((payment, idx) => (
                  <tr key={payment.paymentId || idx} className="hover:bg-gray-50 dark:hover:bg-slate-700/50 transition">
                    <td className="px-6 py-4 font-bold text-indigo-600 dark:text-indigo-400">{payment.paymentId}</td>
                    <td className="px-6 py-4 text-sm text-gray-900 dark:text-white font-medium">{payment.buyer}</td>
                    <td className="px-6 py-4 text-sm text-gray-900 dark:text-white font-medium">{payment.supplier}</td>
                    <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-300">
                      <span className="flex items-center space-x-1"><Globe className="h-3 w-3" /><span>{payment.route}</span></span>
                    </td>
                    <td className="px-6 py-4 text-sm font-bold text-gray-900 dark:text-white">${payment.amount?.toLocaleString()}</td>
                    <td className="px-6 py-4">{getStatusBadge(payment.status)}</td>
                    <td className="px-6 py-4">{getRiskBadge(payment.risk)}</td>
                    <td className="px-6 py-4">
                      <div className="flex items-center space-x-2">
                        <Link to={`/documents?batchId=${payment.batchId}`} className="px-3 py-1.5 bg-gray-900 hover:bg-black text-white dark:bg-indigo-600 dark:hover:bg-indigo-700 rounded-lg text-xs font-bold transition flex items-center gap-1">
                          <ShieldCheck className="h-3 w-3" /> Verify
                        </Link>
                        {payment.status === 'Funded' && (
                          <button onClick={() => { setTransferBatchId(payment.batchId); setShowTransfer(true); setActionMessage(null); }}
                            className="px-3 py-1.5 bg-blue-50 text-blue-700 hover:bg-blue-100 dark:bg-slate-700 dark:text-blue-400 dark:hover:bg-slate-600 rounded-lg text-xs font-bold transition flex items-center gap-1">
                            <DollarSign className="h-3 w-3" /> Release
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Release Funds Modal */}
      {showTransfer && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-md p-8 animate-fade-in border border-gray-100 dark:border-slate-700">
            <h3 className="text-2xl font-bold mb-6 text-gray-800 dark:text-white flex items-center"><DollarSign className="mr-3 text-indigo-500"/> Release Funds — Payment #{transferBatchId}</h3>
            <form onSubmit={handleTransfer} className="space-y-6">
              <div>
                <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-2 uppercase tracking-wide">Supplier Wallet Address</label>
                <input type="text" value={transferAddress} onChange={(e) => setTransferAddress(e.target.value)}
                  className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-slate-600 bg-gray-50 dark:bg-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none transition" placeholder="0x..." required />
              </div>
              <div className="flex space-x-3 pt-2">
                <button type="button" onClick={() => setShowTransfer(false)} className="flex-1 py-3 bg-gray-100 hover:bg-gray-200 dark:bg-slate-700 dark:hover:bg-slate-600 text-gray-800 dark:text-white font-bold rounded-xl transition">Cancel</button>
                <button type="submit" disabled={actionLoading} className="flex-1 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-xl shadow-lg transition">
                  {actionLoading ? 'Releasing...' : 'Confirm Release'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default BatchExplorer;
