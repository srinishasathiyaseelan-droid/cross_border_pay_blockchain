import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { ShieldCheck, Loader2, CheckCircle, XCircle, AlertCircle, AlertTriangle, FileText, QrCode, Camera, X } from 'lucide-react';
import { seedService } from '../services/api';
import QrCodeDisplay from './QrCodeDisplay';
import QRScanner from './QRScanner';
import { DOCUMENT_TYPES } from '../constants/paymentData';

const CertificateVerifier = () => {
  const location = useLocation();
  const [inputValue, setInputValue] = useState('');
  const [inputType, setInputType] = useState('DOCUMENT'); // 'DOCUMENT' or 'PAYMENT'
  const [scannerOpen, setScannerOpen] = useState(false);

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const searchParams = new URLSearchParams(location.search);
    if (searchParams.has('batchId')) {
      setInputType('PAYMENT');
      setInputValue(searchParams.get('batchId'));
      setTimeout(() => triggerVerification('PAYMENT', searchParams.get('batchId')), 100);
    }
  }, [location.search]);

  const triggerVerification = async (type, id) => {
    if (!id || !String(id).trim()) { 
      setError('Please enter a valid ID'); 
      return; 
    }

    setLoading(true);
    setError(null);
    setResult(null);
    setScannerOpen(false);

    try {
      let certIdToVerify = Number(id);

      if (type === 'PAYMENT') {
        const certData = await seedService.getCertificateByBatch(Number(id));
        certIdToVerify = Number(certData.certId);
      }

      const verificationData = await seedService.verifyCertificate(certIdToVerify);
      setResult(verificationData);

    } catch (err) {
      setError(err.response?.data?.error || err.message || 'Verification failed. No document found for this ID.');
    } finally {
      setLoading(false);
    }
  };

  const handleManualVerify = () => {
    triggerVerification(inputType, inputValue);
  };

  const handleScanSuccess = (decodedText) => {
    try {
      const data = JSON.parse(decodedText);
      if (data.type === 'PAYMENT') {
        setInputType('PAYMENT');
        setInputValue(data.id);
        triggerVerification('PAYMENT', data.id);
      } else if (data.type === 'DOCUMENT') {
        setInputType('DOCUMENT');
        setInputValue(data.id);
        triggerVerification('DOCUMENT', data.id);
      } else {
        setInputValue(decodedText);
        triggerVerification(inputType, decodedText);
      }
    } catch {
      setInputValue(decodedText);
      triggerVerification(inputType, decodedText);
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'VALID': return <CheckCircle className="h-16 w-16 text-emerald-500" />;
      case 'EXPIRED': return <AlertTriangle className="h-16 w-16 text-yellow-500" />;
      case 'TAMPERED': return <XCircle className="h-16 w-16 text-red-500" />;
      case 'REVOKED': return <XCircle className="h-16 w-16 text-red-500" />;
      default: return <AlertCircle className="h-16 w-16 text-gray-400" />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'VALID': return 'bg-emerald-50 dark:bg-emerald-900/30 border-emerald-200 dark:border-emerald-800';
      case 'EXPIRED': return 'bg-yellow-50 dark:bg-yellow-900/30 border-yellow-200 dark:border-yellow-800';
      case 'TAMPERED': return 'bg-red-50 dark:bg-red-900/30 border-red-200 dark:border-red-800';
      case 'REVOKED': return 'bg-red-50 dark:bg-red-900/30 border-red-200 dark:border-red-800';
      default: return 'bg-gray-50 dark:bg-slate-700 border-gray-200 dark:border-slate-600';
    }
  };

  const getStatusText = (status) => {
    switch (status) {
      case 'VALID': return { title: 'Document Verified', desc: 'This trade document is authentic and verified on the blockchain.' };
      case 'EXPIRED': return { title: 'Document Expired', desc: 'The document is authentic but has expired. Please check validity dates.' };
      case 'TAMPERED': return { title: 'Integrity Failure', desc: 'WARNING: Blockchain signatures do not match! Document may have been altered.' };
      case 'REVOKED': return { title: 'Document Revoked', desc: 'This document has been explicitly revoked by the issuing authority.' };
      default: return { title: 'Unknown Status', desc: 'Unable to verify document authenticity.' };
    }
  };

  const mapDocType = (data) => {
    if (data?.documentType) return data.documentType;
    return DOCUMENT_TYPES[0];
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-12 animate-fade-in">
      <div className="mb-10 text-center">
        <h1 className="text-4xl md:text-5xl font-bold bg-gradient-to-r from-indigo-600 to-violet-600 bg-clip-text text-transparent mb-4">
          Trade Document Verification
        </h1>
        <p className="text-lg text-gray-600 dark:text-gray-300 max-w-2xl mx-auto leading-relaxed">
          Verify the authenticity of trade documents (invoices, contracts, shipping documents) recorded on the blockchain.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-12 gap-8 items-start">
        {/* LEFT COLUMN: Controls */}
        <div className="md:col-span-5 space-y-6">
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-xl p-8 border border-gray-100 dark:border-slate-700">
            <h2 className="text-2xl font-bold mb-6 text-gray-800 dark:text-white flex items-center gap-2">
              <ShieldCheck className="h-6 w-6 text-indigo-500" />
              Verify Document
            </h2>

            {!scannerOpen ? (
              <div className="space-y-6">
                <div>
                  <div className="flex bg-gray-100 dark:bg-slate-700 p-1 rounded-lg mb-4">
                    <button 
                      className={`flex-1 py-2 text-sm font-semibold rounded-md transition ${inputType === 'DOCUMENT' ? 'bg-white dark:bg-slate-800 shadow text-indigo-600 dark:text-indigo-400' : 'text-gray-500 hover:text-gray-900'}`}
                      onClick={() => setInputType('DOCUMENT')}
                    >
                      Document ID
                    </button>
                    <button 
                      className={`flex-1 py-2 text-sm font-semibold rounded-md transition ${inputType === 'PAYMENT' ? 'bg-white dark:bg-slate-800 shadow text-indigo-600 dark:text-indigo-400' : 'text-gray-500 hover:text-gray-900'}`}
                      onClick={() => setInputType('PAYMENT')}
                    >
                      Payment ID
                    </button>
                  </div>

                  <input 
                    type="text" 
                    value={inputValue} 
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleManualVerify()}
                    placeholder={`Enter ${inputType === 'PAYMENT' ? 'Payment' : 'Document'} ID`} 
                    className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-slate-600 bg-gray-50 dark:bg-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none transition" 
                    disabled={loading} 
                  />
                </div>
                
                <button 
                  onClick={handleManualVerify} 
                  disabled={loading || !inputValue.trim()}
                  className="w-full py-4 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-bold shadow-lg shadow-indigo-200 dark:shadow-none transition-all flex items-center justify-center space-x-2"
                >
                  {loading ? <><Loader2 className="h-5 w-5 animate-spin" /><span>Verifying...</span></> : <><ShieldCheck className="h-5 w-5" /><span>Verify Now</span></>}
                </button>

                <div className="pt-6 border-t border-gray-100 dark:border-slate-700 relative">
                  <div className="absolute top-0 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-white dark:bg-slate-800 px-3 text-xs text-gray-400 font-bold uppercase tracking-wider">Or</div>
                  <button 
                    onClick={() => setScannerOpen(true)}
                    className="w-full py-4 bg-gray-50 dark:bg-slate-700 hover:bg-gray-100 dark:hover:bg-slate-600 text-gray-800 dark:text-white rounded-xl font-bold border border-gray-200 dark:border-slate-600 transition-all flex items-center justify-center space-x-2"
                  >
                    <QrCode className="h-5 w-5 text-indigo-600" />
                    <span>Scan QR Code</span>
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-4 animate-fade-in">
                <div className="flex justify-between items-center mb-2">
                  <span className="font-semibold text-gray-800 dark:text-white flex items-center"><Camera className="h-4 w-4 mr-2"/>Point at QR Code</span>
                  <button onClick={() => setScannerOpen(false)} className="p-1 text-gray-500 hover:bg-gray-100 rounded-full dark:hover:bg-slate-700"><X className="h-5 w-5"/></button>
                </div>
                <QRScanner onScanSuccess={handleScanSuccess} />
              </div>
            )}
            
            {error && (
              <div className="mt-6 p-4 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-xl flex items-start space-x-3 animate-slide-up">
                <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-red-800 dark:text-red-300 font-medium">{error}</p>
              </div>
            )}
          </div>
        </div>

        {/* RIGHT COLUMN: Results */}
        <div className="md:col-span-7">
          {!result && !loading && !error && (
            <div className="h-full min-h-[300px] flex flex-col items-center justify-center border-2 border-dashed border-gray-200 dark:border-slate-700 rounded-2xl p-10 text-center bg-gray-50 dark:bg-slate-800/50">
              <FileText className="h-16 w-16 text-gray-300 dark:text-slate-600 mb-4" />
              <h3 className="text-xl font-medium text-gray-500 dark:text-gray-400">Awaiting Verification</h3>
              <p className="text-sm text-gray-400 mt-2">Enter a document or payment ID to verify its blockchain record.</p>
            </div>
          )}

          {loading && (
            <div className="h-full min-h-[300px] flex flex-col items-center justify-center border border-gray-100 dark:border-slate-700 rounded-2xl p-10 bg-white dark:bg-slate-800 shadow-xl">
              <Loader2 className="h-12 w-12 text-indigo-500 animate-spin mb-4" />
              <h3 className="text-xl font-bold text-gray-800 dark:text-white">Querying Blockchain...</h3>
            </div>
          )}

          {result && (
            <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-xl overflow-hidden border border-gray-100 dark:border-slate-700 animate-slide-up">
              <div className={`p-8 ${getStatusColor(result.integrityStatus)} flex flex-col md:flex-row items-center gap-6`}>
                <div className="flex-shrink-0 bg-white dark:bg-slate-800 p-4 rounded-full shadow-lg">
                  {getStatusIcon(result.integrityStatus)}
                </div>
                <div className="text-center md:text-left">
                  <h2 className="text-3xl font-extrabold text-gray-900 dark:text-white tracking-tight mb-2">
                    {getStatusText(result.integrityStatus).title}
                  </h2>
                  <p className="text-base text-gray-700 dark:text-gray-300 font-medium">
                    {getStatusText(result.integrityStatus).desc}
                  </p>
                </div>
              </div>

              <div className="p-8 space-y-8">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                  <div><span className="block text-xs text-gray-400 uppercase font-bold tracking-wider mb-1">Document ID</span><div className="text-lg font-bold text-gray-900 dark:text-white">#{result.certId}</div></div>
                  <div><span className="block text-xs text-gray-400 uppercase font-bold tracking-wider mb-1">Payment ID</span><div className="text-lg font-bold text-indigo-600">CP-{String(result.batchId).padStart(3, '0')}</div></div>
                  <div className="col-span-2"><span className="block text-xs text-gray-400 uppercase font-bold tracking-wider mb-1">Verifier Authority</span><div className="font-mono text-sm dark:text-gray-300 break-all bg-gray-50 dark:bg-slate-900 p-2 rounded">{result.issuer}</div></div>
                </div>

                {result.certificateData && (
                  <div className="relative">
                    <div className="absolute inset-0 flex items-center" aria-hidden="true">
                      <div className="w-full border-t border-gray-200 dark:border-slate-700"></div>
                    </div>
                    <div className="relative flex justify-center">
                      <span className="bg-white dark:bg-slate-800 px-3 text-sm font-bold text-gray-500 uppercase tracking-widest">Document Details</span>
                    </div>
                  </div>
                )}

                {result.certificateData && (
                  <div className="grid grid-cols-2 gap-4">
                    {result.certificateData.labName && (
                      <div className="bg-gray-50 dark:bg-slate-700/50 p-4 rounded-xl">
                        <span className="block text-xs text-gray-500 font-semibold mb-1">Issuing Authority</span>
                        <div className="font-bold text-gray-900 dark:text-white">{result.certificateData.labName}</div>
                      </div>
                    )}
                    <div className="bg-gray-50 dark:bg-slate-700/50 p-4 rounded-xl">
                      <span className="block text-xs text-gray-500 font-semibold mb-1">Document Type</span>
                      <div className="font-bold text-gray-900 dark:text-white">{mapDocType(result.certificateData)}</div>
                    </div>
                    {result.certificateData.testStandard && (
                      <div className="bg-gray-50 dark:bg-slate-700/50 p-4 rounded-xl">
                        <span className="block text-xs text-gray-500 font-semibold mb-1">Standard</span>
                        <div className="font-bold text-gray-900 dark:text-white">{result.certificateData.testStandard}</div>
                      </div>
                    )}
                    {result.certificateData.passStatus && (
                      <div className="bg-gray-50 dark:bg-slate-700/50 p-4 rounded-xl flex items-center justify-between">
                        <span className="text-sm font-bold text-gray-500 uppercase tracking-wider">Verification</span>
                        <div className={`text-xl font-black px-4 py-1 rounded-full ${result.certificateData.passStatus === 'PASS' ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'}`}>
                          {result.certificateData.passStatus === 'PASS' ? 'VERIFIED' : 'FAILED'}
                        </div>
                      </div>
                    )}
                  </div>
                )}
                
                <div className="pt-6 border-t border-gray-100 dark:border-slate-700 flex justify-between items-end">
                   <div>
                     <p className="text-xs text-gray-500 dark:text-gray-400 font-bold uppercase tracking-wider mb-2">IPFS Record</p>
                     <code className="text-xs break-all bg-gray-50 text-gray-600 dark:bg-slate-900 dark:text-gray-400 p-2 rounded-lg block max-w-sm">
                       {result.ipfsHash}
                     </code>
                   </div>
                   <QrCodeDisplay data={JSON.stringify({ type: 'DOC_VERIFIED', docId: result.certId, status: result.integrityStatus, paymentId: result.batchId })} size={96} />
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default CertificateVerifier;
