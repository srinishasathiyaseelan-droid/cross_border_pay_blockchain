import React, { useState } from 'react';
import { Globe, Upload, CheckCircle, AlertCircle, Loader2, FileText } from 'lucide-react';
import { BUYER_COMPANIES, SUPPLIER_COMPANIES, CURRENCIES, PAYMENT_PURPOSES, PAYMENT_TERMS, DOCUMENT_TYPES } from '../constants/paymentData';
import { seedService } from '../services/api';
import QrCodeDisplay from './QrCodeDisplay';

const BatchForm = () => {
  const [mode, setMode] = useState('payment'); // 'payment' or 'document'

  // Payment fields
  const [buyerCompany, setBuyerCompany] = useState(BUYER_COMPANIES[0]?.name || '');
  const [supplierCompany, setSupplierCompany] = useState(SUPPLIER_COMPANIES[0]?.name || '');
  const [buyerCountry, setBuyerCountry] = useState('India');
  const [supplierCountry, setSupplierCountry] = useState('Germany');
  const [amount, setAmount] = useState(10000);
  const [currency, setCurrency] = useState('USD');
  const [invoiceNumber, setInvoiceNumber] = useState('INV-2026-1042');
  const [paymentPurpose, setPaymentPurpose] = useState(PAYMENT_PURPOSES[0]);
  const [dueDate, setDueDate] = useState('');
  const [paymentTerms, setPaymentTerms] = useState(PAYMENT_TERMS[1]?.id || 'milestone');

  // Document fields
  const [docPaymentId, setDocPaymentId] = useState('');
  const [docType, setDocType] = useState(DOCUMENT_TYPES[0]);
  const [docAuthority, setDocAuthority] = useState('');
  const [docExpiryDate, setDocExpiryDate] = useState('');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [response, setResponse] = useState(null);

  const handleSubmitPayment = async (e) => {
    e.preventDefault();
    setError(null); setSuccess(null); setResponse(null);
    setLoading(true);

    try {
      // Map payment data to the existing batch API
      const result = await seedService.createBatch({
        cropType: buyerCompany, // repurpose: buyer company
        seedVariety: supplierCompany, // repurpose: supplier company
        quantity: Number(amount),
        expiryDate: dueDate
      });

      if (result.success) {
        setSuccess('✅ Payment agreement created successfully. Transaction recorded on blockchain.');
        setResponse({ type: 'payment', data: result });
      } else {
        setError(result.message || 'Failed to create payment');
      }
    } catch (err) {
      setError(err.response?.data?.error || err.response?.data?.message || err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitDocument = async (e) => {
    e.preventDefault();
    setError(null); setSuccess(null); setResponse(null);
    setLoading(true);

    try {
      const result = await seedService.registerCertificate({
        batchId: Number(docPaymentId),
        certificateData: {
          labName: docAuthority,
          documentType: docType,
          verificationStatus: 'VERIFIED',
          testStandard: 'ISO 9001',
          passStatus: 'PASS'
        },
        expiryDate: docExpiryDate
      });

      if (result.success) {
        setSuccess('✅ Trade document verified and recorded on blockchain.');
        setResponse({ type: 'document', data: result });
      } else {
        setError(result.message || 'Failed to upload document');
      }
    } catch (err) {
      setError(err.response?.data?.error || err.response?.data?.message || err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-12 animate-fade-in">
      <div className="text-center mb-12">
        <h1 className="text-4xl md:text-5xl font-extrabold bg-gradient-to-r from-indigo-600 to-violet-600 bg-clip-text text-transparent mb-4">
          {mode === 'payment' ? 'Create Cross-Border Payment' : 'Upload Trade Document'}
        </h1>
        <p className="text-lg text-gray-600 dark:text-gray-300 max-w-2xl mx-auto leading-relaxed">
          {mode === 'payment' 
            ? 'Initiate a new cross-border payment agreement. Transaction details are recorded on blockchain and IPFS.'
            : 'Upload and verify trade documents. Document hashes are stored immutably on the blockchain.'}
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Navigation & Forms */}
        <div className="lg:col-span-7 bg-white dark:bg-slate-800 rounded-3xl shadow-xl overflow-hidden border border-gray-100 dark:border-slate-700">
          
          <div className="flex bg-gray-50 dark:bg-slate-900 border-b border-gray-100 dark:border-slate-700">
            <button
              onClick={() => { setMode('payment'); setError(null); setSuccess(null); setResponse(null); }}
              className={`flex-1 flex flex-col items-center justify-center py-6 font-bold transition duration-300 ${
                mode === 'payment' 
                  ? 'bg-white dark:bg-slate-800 text-indigo-600 border-b-4 border-indigo-500 shadow-sm' 
                  : 'text-gray-500 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200'
              }`}
            >
              <Globe className="h-8 w-8 mb-2" />
              <span>Create Payment</span>
            </button>
            <button
              onClick={() => { setMode('document'); setError(null); setSuccess(null); setResponse(null); }}
              className={`flex-1 flex flex-col items-center justify-center py-6 font-bold transition duration-300 ${
                mode === 'document' 
                   ? 'bg-white dark:bg-slate-800 text-indigo-600 border-b-4 border-indigo-500 shadow-sm' 
                   : 'text-gray-500 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200'
              }`}
            >
              <FileText className="h-8 w-8 mb-2" />
              <span>Upload Document</span>
            </button>
          </div>

          <div className="p-8">
            {/* KYC & Blockchain Trust Banner */}
            <div className="mb-6 p-4 bg-gradient-to-r from-emerald-50 to-indigo-50 dark:from-slate-900 dark:to-indigo-950/40 rounded-2xl border border-emerald-200 dark:border-emerald-800 flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="h-3 w-3 bg-emerald-500 rounded-full animate-ping"></div>
                <div>
                  <span className="text-xs font-bold text-emerald-800 dark:text-emerald-300 block">KYC VERIFIED SME PARTICIPANT</span>
                  <span className="text-xs text-gray-600 dark:text-gray-400">Blockchain Smart Contract Escrow Activated</span>
                </div>
              </div>
              <span className="px-3 py-1 bg-emerald-100 text-emerald-800 text-xs font-semibold rounded-full dark:bg-emerald-950 dark:text-emerald-300">
                Compliance Passed
              </span>
            </div>

            {mode === 'payment' && (
              <form onSubmit={handleSubmitPayment} className="space-y-6">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-2 uppercase tracking-wide">Buyer Company</label>
                    <select value={buyerCompany} onChange={(e) => setBuyerCompany(e.target.value)}
                      className="w-full px-4 py-3 rounded-xl border border-gray-300 dark:border-slate-600 bg-gray-50 dark:bg-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none transition" disabled={loading}>
                      {BUYER_COMPANIES.map(c => <option key={c.id} value={c.name}>{c.name}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-2 uppercase tracking-wide">Supplier Company</label>
                    <select value={supplierCompany} onChange={(e) => setSupplierCompany(e.target.value)}
                      className="w-full px-4 py-3 rounded-xl border border-gray-300 dark:border-slate-600 bg-gray-50 dark:bg-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none transition" disabled={loading}>
                      {SUPPLIER_COMPANIES.map(c => <option key={c.id} value={c.name}>{c.name}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-2 uppercase tracking-wide">Amount</label>
                    <input type="number" value={amount} onChange={(e) => setAmount(e.target.value)}
                      className="w-full px-4 py-3 rounded-xl border border-gray-300 dark:border-slate-600 bg-gray-50 dark:bg-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none transition" min="1" required disabled={loading} />
                  </div>
                  <div>
                    <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-2 uppercase tracking-wide">Currency</label>
                    <select value={currency} onChange={(e) => setCurrency(e.target.value)}
                      className="w-full px-4 py-3 rounded-xl border border-gray-300 dark:border-slate-600 bg-gray-50 dark:bg-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none transition" disabled={loading}>
                      {CURRENCIES.map(c => <option key={c.id} value={c.id}>{c.label}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-2 uppercase tracking-wide">Invoice Number</label>
                    <input type="text" value={invoiceNumber} onChange={(e) => setInvoiceNumber(e.target.value)}
                      className="w-full px-4 py-3 rounded-xl border border-gray-300 dark:border-slate-600 bg-gray-50 dark:bg-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none transition" required disabled={loading} />
                  </div>
                  <div>
                    <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-2 uppercase tracking-wide">Due Date</label>
                    <input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)}
                      className="w-full px-4 py-3 rounded-xl border border-gray-300 dark:border-slate-600 bg-gray-50 dark:bg-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none transition"
                      min={new Date().toISOString().split('T')[0]} required disabled={loading} />
                  </div>
                  <div>
                    <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-2 uppercase tracking-wide">Payment Purpose</label>
                    <select value={paymentPurpose} onChange={(e) => setPaymentPurpose(e.target.value)}
                      className="w-full px-4 py-3 rounded-xl border border-gray-300 dark:border-slate-600 bg-gray-50 dark:bg-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none transition" disabled={loading}>
                      {PAYMENT_PURPOSES.map(p => <option key={p} value={p}>{p}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-2 uppercase tracking-wide">Payment Terms</label>
                    <select value={paymentTerms} onChange={(e) => setPaymentTerms(e.target.value)}
                      className="w-full px-4 py-3 rounded-xl border border-gray-300 dark:border-slate-600 bg-gray-50 dark:bg-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none transition" disabled={loading}>
                      {PAYMENT_TERMS.map(t => <option key={t.id} value={t.id}>{t.label}</option>)}
                    </select>
                  </div>
                </div>

                {/* Route Preview */}
                <div className="bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-800 rounded-xl p-4">
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-bold text-indigo-700 dark:text-indigo-300">Route</span>
                    <span className="text-gray-900 dark:text-white font-semibold">
                      {BUYER_COMPANIES.find(c => c.name === buyerCompany)?.country || 'India'} → {SUPPLIER_COMPANIES.find(c => c.name === supplierCompany)?.country || 'Germany'}
                    </span>
                  </div>
                </div>

                <div className="pt-4">
                  <button type="submit" disabled={loading}
                    className={`w-full py-4 text-white font-bold rounded-xl shadow-lg transition-all flex items-center justify-center space-x-2 ${loading ? 'opacity-70 cursor-not-allowed bg-indigo-700' : 'bg-indigo-600 hover:bg-indigo-700 shadow-indigo-200 dark:shadow-none delay-75 hover:-translate-y-1'}`}>
                    {loading ? (
                      <><Loader2 className="h-5 w-5 animate-spin" /><span>Recording on Blockchain...</span></>
                    ) : (
                      <><Upload className="h-5 w-5" /><span>Create Payment Agreement</span></>
                    )}
                  </button>
                </div>
              </form>
            )}

            {mode === 'document' && (
              <form onSubmit={handleSubmitDocument} className="space-y-6">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 bg-slate-50 dark:bg-slate-900 p-6 rounded-2xl border border-slate-100 dark:border-slate-800">
                  <div className="sm:col-span-2">
                    <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-2 uppercase tracking-wide text-blue-600 dark:text-blue-400">Payment ID</label>
                    <input type="number" value={docPaymentId} onChange={(e) => setDocPaymentId(e.target.value)}
                      className="w-full px-4 py-3 rounded-xl border-2 border-blue-200 dark:border-blue-800 bg-white dark:bg-slate-800 dark:text-white outline-none focus:border-blue-500 transition" placeholder="Enter corresponding Payment ID" min="1" required disabled={loading} />
                  </div>

                  <div>
                    <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-2 uppercase tracking-wide mt-2">Document Type</label>
                    <select value={docType} onChange={(e) => setDocType(e.target.value)}
                      className="w-full px-4 py-3 rounded-xl border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-800 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none transition" disabled={loading}>
                      {DOCUMENT_TYPES.map(d => <option key={d} value={d}>{d}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-2 uppercase tracking-wide mt-2">Issuing Authority</label>
                    <input type="text" value={docAuthority} onChange={(e) => setDocAuthority(e.target.value)}
                      className="w-full px-4 py-3 rounded-xl border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-800 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none transition" placeholder="Shipping Authority" required disabled={loading} />
                  </div>
                  <div className="sm:col-span-2">
                    <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-2 uppercase tracking-wide mt-2">Document Expiry Date</label>
                    <input type="date" value={docExpiryDate} onChange={(e) => setDocExpiryDate(e.target.value)}
                      className="w-full px-4 py-3 rounded-xl border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-800 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none transition"
                      min={new Date().toISOString().split('T')[0]} required disabled={loading} />
                  </div>
                </div>

                <div className="pt-4">
                  <button type="submit" disabled={loading || !docPaymentId || !docAuthority}
                    className={`w-full py-4 text-white font-bold rounded-xl shadow-lg transition-all flex items-center justify-center space-x-2 ${loading ? 'opacity-70 cursor-not-allowed bg-blue-700' : 'bg-blue-600 hover:bg-blue-700 shadow-blue-200 dark:shadow-none delay-75 hover:-translate-y-1'}`}>
                    {loading ? (
                      <><Loader2 className="h-5 w-5 animate-spin" /><span>Verifying on Ledger...</span></>
                    ) : (
                      <><FileText className="h-5 w-5" /><span>Upload & Verify Document</span></>
                    )}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>

        {/* Status / Output */}
        <div className="lg:col-span-5 h-full">
          {!error && !success && !response && (
            <div className="h-full min-h-[300px] flex flex-col items-center justify-center border-2 border-dashed border-gray-200 dark:border-slate-700 rounded-3xl p-10 text-center bg-gray-50 dark:bg-slate-800/50">
              <Globe className="h-16 w-16 text-gray-300 dark:text-slate-600 mb-4" />
              <h3 className="text-xl font-medium text-gray-500 dark:text-gray-400">Waiting for Submission</h3>
              <p className="text-sm text-gray-400 mt-2">Fill out payment details and submit to record on the blockchain.</p>
            </div>
          )}

          {error && (
            <div className="h-full p-8 bg-red-50 dark:bg-red-900/20 border-2 border-red-200 dark:border-red-800 rounded-3xl flex flex-col items-center text-center justify-center animate-slide-up">
              <AlertCircle className="h-12 w-12 text-red-500 mb-4" />
              <h3 className="text-xl font-bold text-red-800 dark:text-red-400 mb-2">Transaction Failed</h3>
              <p className="text-red-700 dark:text-red-300 font-medium">{error}</p>
            </div>
          )}

          {success && response && (
            <div className="bg-gradient-to-br from-indigo-50 to-violet-50 dark:from-slate-800 dark:to-slate-700 rounded-3xl shadow-xl overflow-hidden border border-indigo-100 dark:border-slate-600 animate-slide-up">
              <div className="bg-indigo-600 p-6 flex items-center gap-4 text-white">
                <CheckCircle className="h-10 w-10 text-indigo-200" />
                <div>
                  <h3 className="text-xl font-extrabold">{response.type === 'payment' ? `Payment Created` : `Document Verified`}</h3>
                  <p className="text-indigo-100 font-medium text-sm">Blockchain record confirmed successfully.</p>
                </div>
              </div>

              <div className="p-8 space-y-6">
                <div className="space-y-4">
                  <div><span className="block text-xs font-bold text-gray-500 uppercase tracking-widest mb-1">{response.type === 'payment' ? 'Payment' : 'Document'} ID</span><div className="text-3xl font-black text-gray-900 dark:text-white">CP-{String(response.type === 'payment' ? response.data.batchId : response.data.certId).padStart(3, '0')}</div></div>
                  <div><span className="block text-xs font-bold text-gray-500 uppercase tracking-widest mb-1">Tx Hash</span><div className="font-mono text-sm bg-white dark:bg-slate-900 p-2 rounded break-all dark:text-gray-300 border border-gray-100 dark:border-slate-600">{response.data.txHash}</div></div>
                  <div><span className="block text-xs font-bold text-gray-500 uppercase tracking-widest mb-1">IPFS Hash</span><div className="font-mono text-sm bg-white dark:bg-slate-900 p-2 rounded break-all dark:text-gray-300 border border-gray-100 dark:border-slate-600">{response.data.ipfsHash}</div></div>
                  {response.data.riskLevel && (
                    <div><span className="block text-xs font-bold text-gray-500 uppercase tracking-widest mb-1">Risk Assessment</span>
                      <div className={`inline-flex px-3 py-1 rounded-full text-sm font-bold ${response.data.riskLevel === 'HIGH' ? 'bg-red-100 text-red-700' : response.data.riskLevel === 'MEDIUM' ? 'bg-yellow-100 text-yellow-700' : 'bg-green-100 text-green-700'}`}>
                        {response.data.riskLevel} — Score: {Math.round((response.data.fraudScore || 0) * 100)}
                      </div>
                    </div>
                  )}
                </div>

                <div className="border-t border-indigo-100 dark:border-slate-600 pt-6 flex flex-col justify-center items-center">
                  <span className="block text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">Blockchain QR Tag</span>
                  <QrCodeDisplay data={JSON.stringify({ 
                    type: response.type === 'payment' ? 'PAYMENT' : 'DOCUMENT', 
                    id: response.type === 'payment' ? response.data.batchId : response.data.certId,
                    tx: response.data.txHash,
                    ipfs: response.data.ipfsHash
                  })} size={144} />
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default BatchForm;
