import React, { useEffect, useState } from 'react';
import { ShieldCheck, Activity, Globe, Database, Server, Lock, BarChart3, AlertTriangle, CheckCircle, Clock } from 'lucide-react';
import axios from 'axios';

const AdminPage = () => {
    const [metrics, setMetrics] = useState(null);

    useEffect(() => {
        fetchMetrics();
        const interval = setInterval(fetchMetrics, 10000);
        return () => clearInterval(interval);
    }, []);

    const fetchMetrics = async () => {
        try {
            const res = await axios.get('http://localhost:4000/dashboard-metrics');
            setMetrics(res.data);
        } catch (e) { console.error(e); }
    };

    const statCards = [
        { label: 'Total Transactions', value: metrics?.totalBatches || 0, icon: BarChart3, color: 'from-indigo-500 to-violet-600' },
        { label: 'Payment Volume', value: '$1.42M', icon: Globe, color: 'from-emerald-500 to-teal-600' },
        { label: 'Pending Payments', value: 18, icon: Clock, color: 'from-yellow-500 to-orange-500' },
        { label: 'Completed', value: metrics?.activeBatches || 0, icon: CheckCircle, color: 'from-green-500 to-emerald-600' },
        { label: 'Disputed', value: 2, icon: AlertTriangle, color: 'from-red-500 to-rose-600' },
        { label: 'High Risk', value: metrics?.highRiskCount || 0, icon: ShieldCheck, color: 'from-orange-500 to-red-500' },
    ];

    const systemServices = [
        { name: 'Ethereum Blockchain', status: 'Operational', tech: 'Hardhat / Ethereum', icon: Database },
        { name: 'IPFS Storage', status: 'Active', tech: 'IPFS Gateway', icon: Server },
        { name: 'AI Risk Engine', status: 'Online', tech: 'Python / FastAPI / Scikit-learn', icon: Activity },
        { name: 'Smart Contracts', status: 'Deployed', tech: 'Solidity / ethers.js', icon: Lock },
    ];

    return (
        <div className="max-w-6xl mx-auto px-4 py-12 animate-fade-in">
            <div className="mb-10">
                <h1 className="text-4xl md:text-5xl font-extrabold bg-gradient-to-r from-indigo-600 to-violet-600 bg-clip-text text-transparent mb-2">
                    Compliance & Payment Monitoring
                </h1>
                <p className="text-lg text-gray-600 dark:text-gray-300">
                    Administrative overview of cross-border payment activity, compliance status, and system health.
                </p>
            </div>

            {/* Stat Grid */}
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-12">
                {statCards.map((card) => {
                    const Icon = card.icon;
                    return (
                        <div key={card.label} className="bg-white dark:bg-slate-800 p-5 rounded-2xl shadow-lg border border-gray-100 dark:border-slate-700 text-center hover:shadow-xl transition">
                            <div className={`inline-flex items-center justify-center w-10 h-10 bg-gradient-to-r ${card.color} rounded-xl mb-3`}>
                                <Icon className="h-5 w-5 text-white" />
                            </div>
                            <p className="text-2xl font-black text-gray-900 dark:text-white">{card.value}</p>
                            <p className="text-xs text-gray-500 dark:text-gray-400 font-bold uppercase tracking-wider mt-1">{card.label}</p>
                        </div>
                    );
                })}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-12">
                {/* System Health */}
                <div className="bg-white dark:bg-slate-800 p-8 rounded-2xl shadow-xl border border-gray-100 dark:border-slate-700">
                    <h2 className="text-2xl font-bold text-gray-800 dark:text-white mb-6 flex items-center">
                        <Activity className="h-6 w-6 mr-3 text-indigo-500" /> System Health
                    </h2>
                    <div className="space-y-4">
                        {systemServices.map((item) => {
                            const Icon = item.icon;
                            return (
                                <div key={item.name} className="flex justify-between items-center p-4 bg-gray-50 dark:bg-slate-900/50 rounded-xl border border-gray-100 dark:border-slate-700">
                                    <div className="flex items-center space-x-3">
                                        <Icon className="h-5 w-5 text-indigo-500" />
                                        <div>
                                            <span className="text-gray-800 dark:text-white font-bold text-sm">{item.name}</span>
                                            <p className="text-xs text-gray-500 dark:text-gray-400">{item.tech}</p>
                                        </div>
                                    </div>
                                    <span className="px-3 py-1 bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-400 rounded-full text-xs font-black flex items-center gap-1">
                                        <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></span> {item.status}
                                    </span>
                                </div>
                            );
                        })}
                    </div>
                </div>

                {/* Hyperledger Fabric Section */}
                <div className="bg-white dark:bg-slate-800 p-8 rounded-2xl shadow-xl border border-gray-100 dark:border-slate-700">
                    <h2 className="text-2xl font-bold text-gray-800 dark:text-white mb-6 flex items-center">
                        <Globe className="h-6 w-6 mr-3 text-violet-500" /> Enterprise Ledger
                    </h2>
                    <div className="bg-gradient-to-br from-violet-50 to-indigo-50 dark:from-violet-900/20 dark:to-indigo-900/20 p-6 rounded-2xl border border-violet-200 dark:border-violet-800 mb-6">
                        <div className="flex items-center justify-between mb-4">
                            <span className="text-sm font-bold text-violet-700 dark:text-violet-300 uppercase tracking-wider">Technology</span>
                            <span className="text-lg font-black text-gray-900 dark:text-white">Hyperledger Fabric</span>
                        </div>
                        <div className="flex items-center justify-between mb-4">
                            <span className="text-sm font-bold text-violet-700 dark:text-violet-300 uppercase tracking-wider">Status</span>
                            <span className="px-4 py-1 bg-yellow-100 dark:bg-yellow-900/40 text-yellow-700 dark:text-yellow-300 rounded-full text-sm font-bold">
                                Demo / Integration Ready
                            </span>
                        </div>
                    </div>
                    <div className="space-y-3">
                        <h3 className="font-bold text-gray-700 dark:text-gray-300 mb-3">Purpose</h3>
                        {[
                            'Enterprise audit trail',
                            'Business identity management',
                            'Compliance records',
                            'Permissioned transaction records',
                        ].map((purpose) => (
                            <div key={purpose} className="flex items-center space-x-3 p-3 bg-gray-50 dark:bg-slate-700 rounded-xl">
                                <CheckCircle className="h-4 w-4 text-violet-500 flex-shrink-0" />
                                <span className="text-sm text-gray-700 dark:text-gray-300">{purpose}</span>
                            </div>
                        ))}
                    </div>
                    <p className="mt-4 text-xs text-gray-400 dark:text-gray-500 italic">
                        Note: This is a demo representation. No live Hyperledger Fabric network is currently running.
                    </p>
                </div>
            </div>
        </div>
    );
};

export default AdminPage;
