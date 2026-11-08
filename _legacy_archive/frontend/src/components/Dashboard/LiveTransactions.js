import React, { useEffect, useState } from 'react';
import { seedService } from '../../services/api';
import { CreditCard, Clock, FileText, DollarSign, ArrowRightLeft } from 'lucide-react';

const LiveTransactions = () => {
    const [events, setEvents] = useState([]);

    useEffect(() => {
        fetchEvents();
        const interval = setInterval(fetchEvents, 5000);
        return () => clearInterval(interval);
    }, []);

    const fetchEvents = async () => {
        try {
            const data = await seedService.getBlockchainEvents();
            setEvents(data.slice(0, 10));
        } catch (err) {
            console.error("Error fetching events", err);
        }
    };

    const formatTime = (ts) => ts ? new Date(ts * 1000).toLocaleTimeString() : 'N/A';
    const formatAddr = (a) => a ? `${a.slice(0, 6)}...${a.slice(-4)}` : 'N/A';

    const mapType = (type) => {
        switch (type) {
            case 'BatchCreated': return 'PaymentCreated';
            case 'CertificateRegistered': return 'DocVerified';
            case 'BatchTransferred': return 'FundsReleased';
            case 'BatchSplit': return 'MilestoneApproved';
            default: return type;
        }
    };

    const getIcon = (type) => {
        switch (type) {
            case 'BatchCreated': return <CreditCard className="h-4 w-4 text-indigo-600" />;
            case 'CertificateRegistered': return <FileText className="h-4 w-4 text-blue-600" />;
            case 'BatchTransferred': return <DollarSign className="h-4 w-4 text-green-600" />;
            case 'BatchSplit': return <ArrowRightLeft className="h-4 w-4 text-orange-600" />;
            default: return <Clock className="h-4 w-4 text-gray-600" />;
        }
    };

    return (
        <div className="bg-white dark:bg-slate-800 p-6 rounded-lg shadow-lg border border-gray-100 dark:border-slate-700">
            <h2 className="text-2xl font-bold mb-4 text-gray-800 dark:text-white">⛓️ Live Payment Activity</h2>
            <div className="overflow-x-auto">
                <table className="min-w-full table-auto">
                    <thead>
                        <tr className="bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-gray-200">
                            <th className="px-4 py-2 text-left">Time</th>
                            <th className="px-4 py-2 text-left">Event</th>
                            <th className="px-4 py-2 text-left">Details</th>
                            <th className="px-4 py-2 text-left">Tx</th>
                        </tr>
                    </thead>
                    <tbody className="text-gray-600 dark:text-gray-300">
                        {events.length === 0 ? (
                            <tr><td colSpan={4} className="px-4 py-8 text-center text-gray-400">No transactions yet. Create a payment to start!</td></tr>
                        ) : events.map((ev, idx) => (
                            <tr key={`${ev.txHash}-${idx}`} className="border-b dark:border-slate-700 hover:bg-gray-50 dark:hover:bg-slate-700/50 transition">
                                <td className="px-4 py-2 text-sm">{formatTime(ev.timestamp)}</td>
                                <td className="px-4 py-2">
                                    <span className="flex items-center space-x-2">
                                        {getIcon(ev.type)}
                                        <span className="text-sm font-semibold">{mapType(ev.type)}</span>
                                    </span>
                                </td>
                                <td className="px-4 py-2 text-sm">
                                    {ev.type === 'BatchCreated' && <span>Payment CP-{String(ev.batchId).padStart(3, '0')} — ${ev.quantity?.toLocaleString()}</span>}
                                    {ev.type === 'CertificateRegistered' && <span>Doc #{ev.certId} for Payment CP-{String(ev.batchId).padStart(3, '0')}</span>}
                                    {ev.type === 'BatchTransferred' && <span>CP-{String(ev.batchId).padStart(3, '0')}: {formatAddr(ev.fromOwner)} → {formatAddr(ev.toOwner)}</span>}
                                    {ev.type === 'BatchSplit' && <span>CP-{String(ev.parentBatchId).padStart(3, '0')} → Milestone #{ev.childBatchId} (${ev.childQuantity?.toLocaleString()})</span>}
                                </td>
                                <td className="px-4 py-2 font-mono text-xs">{formatAddr(ev.txHash)}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default LiveTransactions;
