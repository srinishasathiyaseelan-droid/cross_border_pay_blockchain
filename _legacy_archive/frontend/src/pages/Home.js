import React from 'react';
import { Globe, CreditCard, Lock, ShieldCheck, ArrowRight, FileText, Database } from 'lucide-react';
import { Link } from 'react-router-dom';

const Home = () => {
  const steps = [
    { number: '1', title: 'Create Payment Agreement', description: 'SME buyer initiates a cross-border payment with supplier details, amount, and payment terms. Data is uploaded to IPFS and anchored on the blockchain.' },
    { number: '2', title: 'Supplier Accepts', description: 'The supplier reviews and accepts the payment agreement. Both parties are linked via smart contract escrow.' },
    { number: '3', title: 'Smart Contract Funded', description: 'Buyer deposits funds into the smart contract escrow. Funds are locked until milestone conditions are met.' },
    { number: '4', title: 'Goods Shipped & Documents Verified', description: 'Trade documents (invoices, bills of lading, delivery proofs) are uploaded to IPFS and verified on-chain.' },
    { number: '5', title: 'AI Risk Analysis & Funds Released', description: 'AI engine monitors for fraud patterns. Upon milestone approval, funds are automatically released to the supplier.' },
  ];

  return (
    <div className="min-h-screen">
      {/* Hero */}
      <div className="relative overflow-hidden bg-gradient-to-br from-indigo-600 via-violet-600 to-purple-700">
        <div className="absolute inset-0 bg-black opacity-10"></div>
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
          <div className="text-center">
            <div className="inline-flex items-center justify-center w-20 h-20 bg-white/20 backdrop-blur-sm rounded-full mb-6">
              <Globe className="h-10 w-10 text-white" />
            </div>
            <h1 className="text-4xl md:text-5xl font-bold text-white mb-4 leading-tight">
              CrossPay:<br />Blockchain-Powered Cross-Border Payments
            </h1>
            <p className="text-xl md:text-2xl text-indigo-100 mb-6 font-light">
              Fast, transparent and automated international payments for SMEs.
            </p>
            <p className="text-lg text-indigo-50 max-w-3xl mx-auto mb-8">
              Smart contract escrow, decentralized document storage, and AI-powered risk detection — reducing costs, delays, and fraud in cross-border trade.
            </p>
            <Link to="/create-payment" className="inline-flex items-center space-x-2 bg-white text-indigo-600 font-semibold py-4 px-8 rounded-lg shadow-xl hover:shadow-2xl transform hover:scale-105 transition-all duration-200">
              <span>Create Payment</span><ArrowRight className="h-5 w-5" />
            </Link>
          </div>
        </div>
      </div>

      {/* Features */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold text-gray-800 dark:text-white mb-4">Core Capabilities</h2>
          <p className="text-gray-600 dark:text-gray-300 max-w-2xl mx-auto">A comprehensive blockchain-powered cross-border payment platform for SMEs</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 mb-16">
          {[
            { icon: Lock, title: 'Smart Contract Escrow', desc: 'Automate payment conditions and milestone-based settlement with trustless smart contracts.', color: 'from-indigo-500 to-indigo-600' },
            { icon: CreditCard, title: 'Blockchain Transparency', desc: 'Track payment events with immutable blockchain records. Every transaction is verifiable.', color: 'from-violet-500 to-violet-600' },
            { icon: FileText, title: 'IPFS Documents', desc: 'Securely reference invoices and trade documents using decentralized, tamper-proof storage.', color: 'from-blue-500 to-blue-600' },
            { icon: ShieldCheck, title: 'Fraud & Risk Monitoring', desc: 'Identify abnormal international payment patterns with AI-powered anomaly detection.', color: 'from-orange-500 to-red-500' },
            { icon: Database, title: 'Enterprise Ledger', desc: 'Support permissioned business and compliance workflows with Hyperledger Fabric integration.', color: 'from-purple-500 to-purple-600' },
          ].map((f, i) => (
            <div key={i} className="card group hover:scale-105 transition-all duration-300 text-center dark:bg-slate-800 dark:border-slate-700">
              <div className={`inline-flex items-center justify-center w-16 h-16 bg-gradient-to-r ${f.color} rounded-xl mb-4 group-hover:scale-110 transition-transform`}>
                <f.icon className="h-8 w-8 text-white" />
              </div>
              <h3 className="text-xl font-bold text-gray-800 dark:text-white mb-2">{f.title}</h3>
              <p className="text-gray-600 dark:text-gray-300 text-sm">{f.desc}</p>
            </div>
          ))}
        </div>

        {/* How It Works */}
        <div className="card bg-gradient-to-br from-gray-50 to-indigo-50 dark:from-slate-800 dark:to-slate-900 border-indigo-200 dark:border-slate-700">
          <h2 className="text-3xl font-bold text-gray-800 dark:text-white mb-8 text-center">Payment Workflow</h2>
          <div className="space-y-6">
            {steps.map((step, index) => (
              <div key={index} className="flex items-start space-x-4 p-4 bg-white dark:bg-slate-800 rounded-lg shadow-sm hover:shadow-md transition-shadow dark:border dark:border-slate-700">
                <div className="flex-shrink-0 w-12 h-12 bg-gradient-to-r from-indigo-600 to-violet-600 text-white rounded-full flex items-center justify-center font-bold text-lg">{step.number}</div>
                <div className="flex-1">
                  <h3 className="text-lg font-bold text-gray-800 dark:text-white mb-2">{step.title}</h3>
                  <p className="text-gray-600 dark:text-gray-300">{step.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="bg-gray-800 dark:bg-slate-950 text-white py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <p className="text-gray-400">CrossPay — Built with React, TailwindCSS, Solidity, Node.js, ethers.js, and Python AI</p>
        </div>
      </div>
    </div>
  );
};

export default Home;
