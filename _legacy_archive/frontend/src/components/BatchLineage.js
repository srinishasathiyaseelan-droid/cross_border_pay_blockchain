import React, { useState } from 'react';
import { Lock, Search, Loader2, DollarSign, ArrowDown, AlertCircle, CheckCircle, Clock, Globe } from 'lucide-react';
import { seedService } from '../services/api';
import { BUYER_COMPANIES, SUPPLIER_COMPANIES } from '../constants/paymentData';

const BatchLineage = () => {
  const [batchId, setBatchId] = useState('');
  const [loading, setLoading] = useState(false);
  const [lineageData, setLineageData] = useState(null);
  const [error, setError] = useState(null);

  const handleSearch = async () => {
    if (!batchId.trim()) return;
    setLoading(true);
    setError(null);
    setLineageData(null);

    try {
      const data = await seedService.getBatchHistory(Number(batchId.replace('CP-', '').replace('cp-', '')));
      setLineageData(data);
    } catch (err) {
      setError(err.response?.data?.error || err.message || 'Failed to fetch payment lifecycle');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (ts) => ts ? new Date(ts * 1000).toLocaleDateString() : 'N/A';
  const formatAddr = (a) => a ? `${a.slice(0, 6)}...${a.slice(-4)}` : 'N/A';

  const getNodeColor = (batch) => {
    if (batch.status === 2) return 'border-green-500 bg-green-50 dark:bg-green-900/20';
    if (batch.expiryDate <= Date.now() / 1000) return 'border-red-500 bg-red-50 dark:bg-red-900/20';
    return 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20';
  };

  const getStatusLabel = (batch) => {
    if (batch.status === 2) return 'Completed';
    if (batch.expiryDate <= Date.now() / 1000) return 'Expired';
    return 'Active';
  };

  // Payment lifecycle steps
  const lifecycleSteps = [
    { label: 'Payment Created', icon: DollarSign, color: 'bg-indigo-500' },
    { label: 'Supplier Accepted', icon: CheckCircle, color: 'bg-blue-500' },
    { label: 'Smart Contract Funded', icon: Lock, color: 'bg-violet-500' },
    { label: 'Goods Shipped', icon: Globe, color: 'bg-teal-500' },
    { label: 'Documents Verified', icon: CheckCircle, color: 'bg-cyan-500' },
    { label: 'Milestone Approved', icon: CheckCircle, color: 'bg-emerald-500' },
    { label: 'Funds Released', icon: DollarSign, color: 'bg-green-500' },
    { label: 'Payment Completed', icon: CheckCircle, color: 'bg-green-600' },
  ];

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 animate-fade-in">
      <div className="mb-8 text-center">
        <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-r from-indigo-600 to-violet-600 rounded-full mb-4">
          <Lock className="h-8 w-8 text-white" />
        </div>
        <h1 className="text-4xl font-bold bg-gradient-to-r from-indigo-600 to-violet-600 bg-clip-text text-transparent mb-2">Payment Escrow & Lifecycle</h1>
        <p className="text-gray-600 dark:text-gray-300">Track the full lifecycle of a cross-border payment through smart contract escrow</p>
      </div>

      {/* Payment Lifecycle Visual */}
      <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-xl p-8 border border-gray-100 dark:border-slate-700 mb-8">
        <h2 className="text-xl font-bold text-gray-800 dark:text-white mb-6">Payment Lifecycle</h2>
        <div className="flex flex-wrap items-center justify-center gap-2">
          {lifecycleSteps.map((step, i) => {
            const Icon = step.icon;
            return (
              <React.Fragment key={step.label}>
                <div className="flex items-center space-x-2 px-3 py-2 bg-gray-50 dark:bg-slate-700 rounded-xl">
                  <div className={`w-6 h-6 ${step.color} rounded-full flex items-center justify-center`}>
                    <Icon className="h-3 w-3 text-white" />
                  </div>
                  <span className="text-xs font-bold text-gray-700 dark:text-gray-300 whitespace-nowrap">{step.label}</span>
                </div>
                {i < lifecycleSteps.length - 1 && <span className="text-gray-400 font-bold">→</span>}
              </React.Fragment>
            );
          })}
        </div>
      </div>

      <div className="card dark:bg-slate-800 mb-8">
        <div className="flex space-x-3">
          <input type="text" value={batchId} onChange={(e) => setBatchId(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="Enter Payment ID (e.g. 1 or CP-001)..." className="input-field flex-1 dark:bg-slate-700 dark:border-slate-600 dark:text-white" />
          <button onClick={handleSearch} disabled={loading || !batchId.trim()}
            className="btn-primary px-6 bg-indigo-600 hover:bg-indigo-700 flex items-center space-x-2">
            {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Search className="h-5 w-5" />}
            <span>Trace</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg flex items-start space-x-3 mb-6">
          <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-red-800 dark:text-red-300">{error}</p>
        </div>
      )}

      {lineageData && (
        <div className="space-y-2">
          <h2 className="text-xl font-bold text-gray-800 dark:text-white mb-4">📋 Escrow History</h2>

          {/* Parent Chain */}
          <div className="relative">
            {lineageData.lineage.map((batch, index) => {
              const buyer = BUYER_COMPANIES[index % BUYER_COMPANIES.length];
              const supplier = SUPPLIER_COMPANIES[index % SUPPLIER_COMPANIES.length];
              return (
                <div key={batch.batchId}>
                  <div className={`border-l-4 ${getNodeColor(batch)} rounded-lg p-4 ml-6 relative`}>
                    <div className="absolute -left-[26px] top-4 w-4 h-4 rounded-full bg-white dark:bg-slate-900 border-4 border-indigo-500"></div>

                    <div className="flex justify-between items-start">
                      <div>
                        <span className="text-xs text-indigo-600 dark:text-indigo-400 font-mono">Payment CP-{String(batch.batchId).padStart(3, '0')}</span>
                        <h3 className="text-lg font-bold text-gray-900 dark:text-white">{buyer.name} → {supplier.name}</h3>
                      </div>
                      <span className={`px-2 py-1 text-xs font-bold rounded-full ${
                        getStatusLabel(batch) === 'Completed' ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300'
                        : getStatusLabel(batch) === 'Expired' ? 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300'
                        : 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300'
                      }`}>
                        {getStatusLabel(batch)}
                      </span>
                    </div>

                    <div className="grid grid-cols-3 gap-4 mt-3 text-sm">
                      <div><span className="text-xs text-gray-500 dark:text-gray-400">Escrow Amount</span><div className="font-semibold dark:text-white">${batch.quantity?.toLocaleString()}</div></div>
                      <div><span className="text-xs text-gray-500 dark:text-gray-400">Due Date</span><div className="font-semibold dark:text-white">{formatDate(batch.expiryDate)}</div></div>
                      <div><span className="text-xs text-gray-500 dark:text-gray-400">Contract</span><div className="font-mono text-xs dark:text-gray-300">{formatAddr(batch.ownerAddress)}</div></div>
                    </div>

                    {batch.parentBatchId > 0 && (
                      <div className="mt-2 text-xs text-indigo-600 dark:text-indigo-400 font-semibold">↑ Milestone from Payment CP-{String(batch.parentBatchId).padStart(3, '0')}</div>
                    )}
                  </div>

                  {index < lineageData.lineage.length - 1 && (
                    <div className="flex items-center justify-center py-1 ml-6">
                      <ArrowDown className="h-5 w-5 text-gray-400 dark:text-gray-500" />
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Children */}
          {lineageData.childBatchIds && lineageData.childBatchIds.length > 0 && (
            <div className="mt-6 p-4 bg-indigo-50 dark:bg-indigo-900/20 rounded-lg border border-indigo-200 dark:border-indigo-800">
              <h3 className="font-bold text-indigo-800 dark:text-indigo-300 mb-2">💰 Partial Releases (Milestones)</h3>
              <div className="flex flex-wrap gap-2">
                {lineageData.childBatchIds.map(childId => (
                  <button key={childId} onClick={() => { setBatchId(String(childId)); }}
                    className="px-3 py-1 bg-indigo-100 dark:bg-indigo-800 text-indigo-700 dark:text-indigo-200 rounded-full text-sm font-semibold hover:bg-indigo-200 dark:hover:bg-indigo-700 transition">
                    Milestone CP-{String(childId).padStart(3, '0')}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default BatchLineage;
