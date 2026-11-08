import React, { useEffect, useState } from 'react';
import { Shield, AlertTriangle, CheckCircle, TrendingUp, Activity } from 'lucide-react';
import axios from 'axios';
import { RISK_FACTORS } from '../constants/paymentData';

const RiskMonitoring = () => {
    const [anomalies, setAnomalies] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchAnomalies();
    }, []);

    const fetchAnomalies = async () => {
        try {
            const res = await axios.get('http://localhost:4000/api/anomalies/recent/alerts?limit=20');
            setAnomalies(res.data || []);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const getRiskColor = (score) => {
        if (score >= 71) return { bg: 'bg-red-100 dark:bg-red-900/40', text: 'text-red-700 dark:text-red-300', label: 'HIGH', bar: 'bg-red-500' };
        if (score >= 31) return { bg: 'bg-yellow-100 dark:bg-yellow-900/40', text: 'text-yellow-700 dark:text-yellow-300', label: 'MEDIUM', bar: 'bg-yellow-500' };
        return { bg: 'bg-green-100 dark:bg-green-900/40', text: 'text-green-700 dark:text-green-300', label: 'LOW', bar: 'bg-green-500' };
    };

    const demoAlerts = [
        { id: 'CP-004', score: 78, reasons: ['Large transaction amount', 'New supplier', 'Country risk'], amount: '$75,000', route: 'India → UK' },
        { id: 'CP-007', score: 62, reasons: ['Unusual transaction frequency', 'Abnormal payment pattern'], amount: '$42,000', route: 'India → UAE' },
        { id: 'CP-003', score: 45, reasons: ['First-time trade route'], amount: '$50,000', route: 'India → France' },
        { id: 'CP-001', score: 12, reasons: ['Normal transaction amount', 'Verified supplier'], amount: '$10,000', route: 'India → Germany' },
        { id: 'CP-002', score: 8, reasons: ['Normal payment frequency'], amount: '$25,000', route: 'India → USA' },
    ];

    return (
        <div className="max-w-6xl mx-auto px-4 py-12 animate-fade-in">
            <div className="mb-10 text-center">
                <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-r from-orange-500 to-red-500 rounded-full mb-4">
                    <Shield className="h-8 w-8 text-white" />
                </div>
                <h1 className="text-4xl md:text-5xl font-extrabold bg-gradient-to-r from-orange-500 to-red-500 bg-clip-text text-transparent mb-4">
                    Risk Monitoring
                </h1>
                <p className="text-lg text-gray-600 dark:text-gray-300 max-w-2xl mx-auto">
                    Cross-border payment risk analysis powered by AI. Identify abnormal international payment patterns in real-time.
                </p>
            </div>

            {/* Risk Factor Legend */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-10">
                {[
                    { label: 'LOW RISK', range: '0 – 30', color: 'from-green-500 to-emerald-500', icon: CheckCircle },
                    { label: 'MEDIUM RISK', range: '31 – 70', color: 'from-yellow-500 to-orange-500', icon: TrendingUp },
                    { label: 'HIGH RISK', range: '71 – 100', color: 'from-red-500 to-rose-600', icon: AlertTriangle },
                ].map((item) => (
                    <div key={item.label} className="bg-white dark:bg-slate-800 rounded-2xl p-6 shadow-lg border border-gray-100 dark:border-slate-700 text-center">
                        <div className={`inline-flex items-center justify-center w-12 h-12 bg-gradient-to-r ${item.color} rounded-xl mb-3`}>
                            <item.icon className="h-6 w-6 text-white" />
                        </div>
                        <h3 className="font-bold text-gray-900 dark:text-white">{item.label}</h3>
                        <p className="text-sm text-gray-500 dark:text-gray-400">Score: {item.range}</p>
                    </div>
                ))}
            </div>

            {/* Risk Factors */}
            <div className="bg-white dark:bg-slate-800 rounded-2xl p-8 shadow-xl border border-gray-100 dark:border-slate-700 mb-10">
                <h2 className="text-2xl font-bold text-gray-800 dark:text-white mb-6 flex items-center">
                    <Activity className="h-6 w-6 mr-3 text-orange-500" /> Monitored Risk Factors
                </h2>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    {RISK_FACTORS.map((factor) => (
                        <div key={factor} className="bg-gray-50 dark:bg-slate-700 px-4 py-3 rounded-xl text-sm font-medium text-gray-700 dark:text-gray-300 border border-gray-100 dark:border-slate-600">
                            {factor}
                        </div>
                    ))}
                </div>
            </div>

            {/* Alert List */}
            <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-xl border border-gray-100 dark:border-slate-700 overflow-hidden">
                <div className="p-6 border-b border-gray-100 dark:border-slate-700">
                    <h2 className="text-2xl font-bold text-gray-800 dark:text-white">Recent Risk Assessments</h2>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">AI-powered analysis of cross-border payment risk</p>
                </div>
                <div className="divide-y divide-gray-100 dark:divide-slate-700">
                    {demoAlerts.map((alert) => {
                        const risk = getRiskColor(alert.score);
                        return (
                            <div key={alert.id} className="p-6 hover:bg-gray-50 dark:hover:bg-slate-700/50 transition">
                                <div className="flex items-center justify-between mb-3">
                                    <div className="flex items-center space-x-4">
                                        <span className="text-lg font-bold text-indigo-600 dark:text-indigo-400">{alert.id}</span>
                                        <span className="text-sm text-gray-500 dark:text-gray-400">{alert.route}</span>
                                        <span className="text-sm font-semibold text-gray-900 dark:text-white">{alert.amount}</span>
                                    </div>
                                    <div className="flex items-center space-x-3">
                                        <span className="text-2xl font-black text-gray-900 dark:text-white">{alert.score}</span>
                                        <span className={`px-3 py-1 text-xs font-bold rounded-full ${risk.bg} ${risk.text}`}>{risk.label}</span>
                                    </div>
                                </div>
                                <div className="w-full bg-gray-200 dark:bg-slate-600 rounded-full h-2 mb-3">
                                    <div className={`${risk.bar} h-2 rounded-full transition-all`} style={{ width: `${alert.score}%` }}></div>
                                </div>
                                <div className="flex flex-wrap gap-2">
                                    {alert.reasons.map((r) => (
                                        <span key={r} className="px-2 py-1 text-xs bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-gray-400 rounded-lg">{r}</span>
                                    ))}
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>
        </div>
    );
};

export default RiskMonitoring;
