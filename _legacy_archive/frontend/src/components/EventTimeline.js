import React, { useState, useEffect } from 'react';
import { Clock, Copy, CheckCircle, Loader2, AlertCircle, CreditCard, FileText, DollarSign, ArrowRightLeft } from 'lucide-react';
import { seedService } from '../services/api';

const EventTimeline = () => {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [copiedHash, setCopiedHash] = useState(null);

  useEffect(() => { fetchEvents(); }, []);

  const fetchEvents = async () => {
    try {
      setLoading(true);
      const data = await seedService.getBlockchainEvents();
      setEvents(data);
    } catch (err) {
      setError(err.message || 'Failed to fetch events');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    setCopiedHash(text);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  const formatTimestamp = (ts) => {
    if (!ts) return 'N/A';
    return new Date(ts * 1000).toLocaleString();
  };

  const formatAddr = (a) => a ? `${a.slice(0, 6)}...${a.slice(-4)}` : 'N/A';

  // Map seed events to payment events
  const mapEventType = (type) => {
    switch (type) {
      case 'BatchCreated': return 'PaymentCreated';
      case 'CertificateRegistered': return 'DocumentVerified';
      case 'BatchTransferred': return 'FundsReleased';
      case 'BatchSplit': return 'MilestoneApproved';
      default: return type;
    }
  };

  const getEventIcon = (type) => {
    switch (type) {
      case 'BatchCreated': return <CreditCard className="h-5 w-5 text-indigo-600" />;
      case 'CertificateRegistered': return <FileText className="h-5 w-5 text-blue-600" />;
      case 'BatchTransferred': return <DollarSign className="h-5 w-5 text-green-600" />;
      case 'BatchSplit': return <ArrowRightLeft className="h-5 w-5 text-orange-600" />;
      default: return <Clock className="h-5 w-5 text-gray-600" />;
    }
  };

  const getEventColor = (type) => {
    switch (type) {
      case 'BatchCreated': return 'border-l-indigo-500';
      case 'CertificateRegistered': return 'border-l-blue-500';
      case 'BatchTransferred': return 'border-l-green-500';
      case 'BatchSplit': return 'border-l-orange-500';
      default: return 'border-l-gray-500';
    }
  };

  const getEventBadgeColor = (type) => {
    switch (type) {
      case 'BatchCreated': return 'bg-indigo-100 dark:bg-indigo-900/40 text-indigo-800 dark:text-indigo-300';
      case 'CertificateRegistered': return 'bg-blue-100 dark:bg-blue-900/40 text-blue-800 dark:text-blue-300';
      case 'BatchTransferred': return 'bg-green-100 dark:bg-green-900/40 text-green-800 dark:text-green-300';
      case 'BatchSplit': return 'bg-orange-100 dark:bg-orange-900/40 text-orange-800 dark:text-orange-300';
      default: return 'bg-gray-100 dark:bg-slate-600 text-gray-800 dark:text-gray-300';
    }
  };

  if (loading) return (
    <div className="flex justify-center items-center min-h-[400px]">
      <div className="text-center"><Loader2 className="h-12 w-12 text-indigo-600 animate-spin mx-auto mb-4" /><p className="text-gray-600">Loading blockchain transactions...</p></div>
    </div>
  );

  if (error) return (
    <div className="max-w-4xl mx-auto px-4 py-8"><div className="card bg-red-50 dark:bg-red-900/30 border-red-200 dark:border-red-800"><div className="flex items-center space-x-3"><AlertCircle className="h-6 w-6 text-red-600" /><p className="text-red-800 dark:text-red-300">{error}</p></div></div></div>
  );

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 animate-fade-in">
      <div className="mb-8">
        <h1 className="text-4xl font-bold bg-gradient-to-r from-indigo-600 to-violet-600 bg-clip-text text-transparent mb-2">⛓️ Blockchain Transactions</h1>
        <p className="text-gray-600 dark:text-gray-300">All cross-border payment events recorded on the blockchain ({events.length} transactions)</p>
      </div>

      {events.length === 0 ? (
        <div className="text-center py-16"><Clock className="h-16 w-16 text-gray-400 mx-auto mb-4" /><h2 className="text-2xl font-bold text-gray-700 dark:text-gray-300">No transactions yet</h2><p className="text-gray-600 dark:text-gray-400">Create a payment to start!</p></div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {events.map((event, idx) => (
            <div key={`${event.txHash}-${idx}`} className={`card dark:bg-slate-800 group hover:scale-[1.02] transition-transform border-l-4 ${getEventColor(event.type)}`}>
              <div className="flex justify-between items-start mb-3">
                <span className={`px-3 py-1 text-xs font-semibold rounded-full flex items-center space-x-1 ${getEventBadgeColor(event.type)}`}>
                  {getEventIcon(event.type)}<span className="ml-1">{mapEventType(event.type)}</span>
                </span>
              </div>

              <div className="space-y-2 text-sm">
                {event.type === 'BatchCreated' && (
                  <>
                    <div className="flex justify-between"><span className="text-gray-500 dark:text-gray-400">Payment</span><span className="font-bold dark:text-white">CP-{String(event.batchId).padStart(3, '0')}</span></div>
                    <div className="flex justify-between"><span className="text-gray-500 dark:text-gray-400">Buyer</span><span className="font-semibold dark:text-white">{event.cropType}</span></div>
                    <div className="flex justify-between"><span className="text-gray-500 dark:text-gray-400">Amount</span><span className="dark:text-white">${event.quantity?.toLocaleString()}</span></div>
                  </>
                )}

                {event.type === 'CertificateRegistered' && (
                  <>
                    <div className="flex justify-between"><span className="text-gray-500 dark:text-gray-400">Doc ID</span><span className="font-bold dark:text-white">#{event.certId}</span></div>
                    <div className="flex justify-between"><span className="text-gray-500 dark:text-gray-400">Payment</span><span className="font-bold dark:text-white">CP-{String(event.batchId).padStart(3, '0')}</span></div>
                    <div className="flex justify-between"><span className="text-gray-500 dark:text-gray-400">Verifier</span><span className="font-mono text-xs dark:text-gray-300">{formatAddr(event.issuer)}</span></div>
                  </>
                )}

                {event.type === 'BatchTransferred' && (
                  <>
                    <div className="flex justify-between"><span className="text-gray-500 dark:text-gray-400">Payment</span><span className="font-bold dark:text-white">CP-{String(event.batchId).padStart(3, '0')}</span></div>
                    <div className="flex justify-between"><span className="text-gray-500 dark:text-gray-400">From</span><span className="font-mono text-xs dark:text-gray-300">{formatAddr(event.fromOwner)}</span></div>
                    <div className="flex justify-between"><span className="text-gray-500 dark:text-gray-400">To</span><span className="font-mono text-xs dark:text-gray-300">{formatAddr(event.toOwner)}</span></div>
                  </>
                )}

                {event.type === 'BatchSplit' && (
                  <>
                    <div className="flex justify-between"><span className="text-gray-500 dark:text-gray-400">Payment</span><span className="font-bold dark:text-white">CP-{String(event.parentBatchId).padStart(3, '0')}</span></div>
                    <div className="flex justify-between"><span className="text-gray-500 dark:text-gray-400">Milestone</span><span className="font-bold text-indigo-600 dark:text-indigo-400">#{event.childBatchId}</span></div>
                    <div className="flex justify-between"><span className="text-gray-500 dark:text-gray-400">Amount</span><span className="dark:text-white">${event.childQuantity?.toLocaleString()}</span></div>
                  </>
                )}

                <div className="pt-2 border-t border-gray-100 dark:border-slate-700">
                  <div className="flex justify-between items-center"><span className="text-gray-500 dark:text-gray-400"><Clock className="h-3 w-3 inline mr-1" />Time</span><span className="text-xs dark:text-gray-300">{formatTimestamp(event.timestamp)}</span></div>
                </div>

                {event.txHash && (
                  <div className="flex items-center space-x-2 bg-gray-50 dark:bg-slate-700 p-2 rounded-lg">
                    <span className="font-mono text-xs text-gray-900 dark:text-gray-200 break-all flex-1">{formatAddr(event.txHash)}</span>
                    <button onClick={() => copyToClipboard(event.txHash)} className="p-1 hover:bg-gray-200 dark:hover:bg-slate-600 rounded transition-colors">
                      {copiedHash === event.txHash ? <CheckCircle className="h-4 w-4 text-green-600" /> : <Copy className="h-4 w-4 text-gray-600 dark:text-gray-400" />}
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default EventTimeline;
