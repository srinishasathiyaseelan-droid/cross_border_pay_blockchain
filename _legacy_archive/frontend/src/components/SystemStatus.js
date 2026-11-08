import React, { useState, useEffect } from 'react';

const SystemStatus = () => {
    const [status, setStatus] = useState({
        blockchain: false,
        ipfs: false,
        ai: false,
        lastSync: Date.now()
    });

    const checkHealth = async () => {
        const newStatus = { lastSync: Date.now(), blockchain: false, ipfs: false, ai: false };

        // Check Backend/Blockchain by pinging our own API
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 3000);
            const res = await fetch('http://localhost:4000/dashboard-metrics', {
                signal: controller.signal
            });
            clearTimeout(timeoutId);
            if (res.ok) {
                newStatus.blockchain = true;
            }
        } catch (e) {
            newStatus.blockchain = false;
        }

        // Check IPFS (local gateway)
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 3000);
            await fetch('http://localhost:8080/ipfs/QmUNLLsPGWtnA3CDxEn72KJydbWa1Xp8F59J4J4jQx9nB', {
                method: 'HEAD',
                signal: controller.signal,
                mode: 'no-cors'
            });
            newStatus.ipfs = true;
            clearTimeout(timeoutId);
        } catch (e) {
            newStatus.ipfs = false;
        }

        // Check AI Engine
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 3000);
            const res = await fetch('http://localhost:5000/model-health', {
                signal: controller.signal
            });
            clearTimeout(timeoutId);
            if (res.ok) {
                newStatus.ai = true;
            }
        } catch (e) { newStatus.ai = false; }

        setStatus(newStatus);
    };

    useEffect(() => {
        checkHealth();
        const interval = setInterval(checkHealth, 10000);
        return () => clearInterval(interval);
    }, []);

    const StatusDot = ({ label, active }) => (
        <div className="flex items-center space-x-2 bg-gray-50 dark:bg-slate-800 px-2 py-1 rounded border border-gray-200 dark:border-slate-700">
            <div className={`h-2 w-2 rounded-full ${active ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></div>
            <span className="text-xs font-medium text-gray-600 dark:text-gray-400 hidden lg:inline-block">{label}</span>
        </div>
    );

    return (
        <div className="flex items-center space-x-4 pr-4 mr-2">
            <StatusDot label="Blockchain" active={status.blockchain} />
            <StatusDot label="IPFS" active={status.ipfs} />
            <StatusDot label="Risk Engine" active={status.ai} />
        </div>
    );
};

export default SystemStatus;
