import React from 'react';
import { Settings, Wallet, Globe, Server, Info } from 'lucide-react';
import { useWallet } from '../context/WalletContext';
import WalletConnector from '../components/WalletConnector';

const SettingsPage = () => {
    const { isConnected, account } = useWallet();

    return (
        <div className="max-w-4xl mx-auto px-4 py-12 animate-fade-in">
            <div className="mb-10">
                <h1 className="text-4xl md:text-5xl font-extrabold bg-gradient-to-r from-indigo-600 to-violet-600 bg-clip-text text-transparent mb-2">
                    Settings
                </h1>
                <p className="text-lg text-gray-600 dark:text-gray-300">Platform configuration and wallet management</p>
            </div>

            <div className="space-y-8">
                {/* Wallet */}
                <div className="bg-white dark:bg-slate-800 p-8 rounded-2xl shadow-xl border border-gray-100 dark:border-slate-700">
                    <h2 className="text-2xl font-bold text-gray-800 dark:text-white mb-6 flex items-center">
                        <Wallet className="h-6 w-6 mr-3 text-indigo-500" /> Wallet Configuration
                    </h2>
                    <div className="space-y-4">
                        <div className="flex justify-between items-center p-4 bg-gray-50 dark:bg-slate-900/50 rounded-xl">
                            <span className="text-gray-600 dark:text-gray-300 font-semibold">Status</span>
                            <span className={`px-3 py-1 rounded-full text-xs font-bold ${isConnected ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300' : 'bg-gray-100 text-gray-600 dark:bg-slate-700 dark:text-gray-400'}`}>
                                {isConnected ? 'Connected' : 'Not Connected'}
                            </span>
                        </div>
                        {isConnected && account && (
                            <div className="flex justify-between items-center p-4 bg-gray-50 dark:bg-slate-900/50 rounded-xl">
                                <span className="text-gray-600 dark:text-gray-300 font-semibold">Address</span>
                                <span className="font-mono text-sm text-gray-900 dark:text-white">{account}</span>
                            </div>
                        )}
                        <div className="flex justify-between items-center p-4 bg-gray-50 dark:bg-slate-900/50 rounded-xl">
                            <span className="text-gray-600 dark:text-gray-300 font-semibold">Network</span>
                            <span className="text-gray-900 dark:text-white font-semibold">Hardhat Local (Chain ID: 31337)</span>
                        </div>
                        <div className="pt-4">
                            <WalletConnector />
                        </div>
                    </div>
                </div>

                {/* Network */}
                <div className="bg-white dark:bg-slate-800 p-8 rounded-2xl shadow-xl border border-gray-100 dark:border-slate-700">
                    <h2 className="text-2xl font-bold text-gray-800 dark:text-white mb-6 flex items-center">
                        <Globe className="h-6 w-6 mr-3 text-indigo-500" /> Network Configuration
                    </h2>
                    <div className="space-y-4">
                        {[
                            { label: 'Backend API', value: 'http://localhost:4000' },
                            { label: 'AI Risk Engine', value: 'http://localhost:5000' },
                            { label: 'Blockchain RPC', value: 'http://localhost:8545' },
                            { label: 'IPFS Gateway', value: 'http://localhost:8080' },
                        ].map((item) => (
                            <div key={item.label} className="flex justify-between items-center p-4 bg-gray-50 dark:bg-slate-900/50 rounded-xl">
                                <span className="text-gray-600 dark:text-gray-300 font-semibold">{item.label}</span>
                                <code className="text-sm font-mono text-indigo-600 dark:text-indigo-400">{item.value}</code>
                            </div>
                        ))}
                    </div>
                </div>

                {/* About */}
                <div className="bg-white dark:bg-slate-800 p-8 rounded-2xl shadow-xl border border-gray-100 dark:border-slate-700">
                    <h2 className="text-2xl font-bold text-gray-800 dark:text-white mb-6 flex items-center">
                        <Info className="h-6 w-6 mr-3 text-indigo-500" /> About CrossPay
                    </h2>
                    <p className="text-gray-600 dark:text-gray-300 leading-relaxed mb-4">
                        CrossPay is a blockchain-enabled cross-border payment platform for SMEs. It demonstrates how smart contracts, 
                        decentralized storage (IPFS), and AI-powered risk detection can reduce transaction costs, settlement delays, 
                        and payment fraud in international trade.
                    </p>
                    <div className="flex flex-wrap gap-2">
                        {['React', 'Tailwind CSS', 'Node.js', 'Solidity', 'Hardhat', 'ethers.js', 'IPFS', 'Python', 'FastAPI', 'Scikit-learn'].map((tech) => (
                            <span key={tech} className="px-3 py-1 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 rounded-full text-xs font-bold">
                                {tech}
                            </span>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default SettingsPage;
