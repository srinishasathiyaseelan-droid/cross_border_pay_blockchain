import React, { useState, useEffect } from 'react';
import { ShieldCheck, UserCheck, Building, Globe, FileText, CheckCircle2, AlertTriangle, Lock } from 'lucide-react';
import { useWallet } from '../context/WalletContext';
import axios from 'axios';

const KYCPage = () => {
  const { isConnected, account } = useWallet();
  const [formData, setFormData] = useState({
    companyName: '',
    registrationNumber: '',
    country: 'United States',
    idType: 'Business License & Tax ID',
    documentFile: null
  });

  const [kycStatus, setKycStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [successMsg, setSuccessMsg] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    if (account) {
      fetchKYCStatus(account);
    }
  }, [account]);

  const fetchKYCStatus = async (walletAddress) => {
    try {
      const res = await axios.get(`http://localhost:4000/api/kyc/${walletAddress}`);
      if (res.data && res.data.status === 'VERIFIED') {
        setKycStatus(res.data);
      } else {
        setKycStatus(null);
      }
    } catch (err) {
      console.error('Error fetching KYC status:', err);
    }
  };

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!isConnected || !account) {
      setErrorMsg('Please connect your Web3 wallet (MetaMask) first!');
      return;
    }

    setLoading(true);
    setErrorMsg('');
    setSuccessMsg('');

    try {
      const res = await axios.post('http://localhost:4000/api/kyc', {
        walletAddress: account,
        ...formData
      });

      if (res.data.success) {
        setKycStatus(res.data.kyc);
        setSuccessMsg('KYC Verification Completed & Recorded on CrossPay Trust Ledger!');
      }
    } catch (err) {
      setErrorMsg(err.response?.data?.message || 'KYC submission failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-indigo-700 via-violet-700 to-purple-800 rounded-2xl p-8 text-white shadow-xl mb-8">
        <div className="flex items-center space-x-4 mb-4">
          <div className="p-3 bg-white/10 rounded-xl backdrop-blur-sm">
            <ShieldCheck className="h-8 w-8 text-emerald-400" />
          </div>
          <div>
            <h1 className="text-3xl font-bold">KYC & Compliance Verification</h1>
            <p className="text-indigo-200 mt-1 text-sm">
              SME Identity Verification for International Cross-Border Trade & Escrow Safety
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6 pt-6 border-t border-indigo-500/30">
          <div className="flex items-center space-x-3 bg-white/5 p-3 rounded-lg">
            <UserCheck className="h-5 w-5 text-indigo-300" />
            <span className="text-xs">MetaMask Wallet Identity Linked</span>
          </div>
          <div className="flex items-center space-x-3 bg-white/5 p-3 rounded-lg">
            <Lock className="h-5 w-5 text-emerald-300" />
            <span className="text-xs">Smart Contract AML Compliance</span>
          </div>
          <div className="flex items-center space-x-3 bg-white/5 p-3 rounded-lg">
            <CheckCircle2 className="h-5 w-5 text-purple-300" />
            <span className="text-xs">Instant Fraud Prevention Rating</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Form */}
        <div className="lg:col-span-2 bg-white dark:bg-slate-900 rounded-2xl p-6 shadow-lg border border-gray-100 dark:border-slate-800">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-6 flex items-center gap-2">
            <Building className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
            Submit Enterprise KYC Details
          </h2>

          {!isConnected ? (
            <div className="bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 rounded-xl p-6 text-center">
              <AlertTriangle className="h-10 w-10 text-amber-500 mx-auto mb-3" />
              <h3 className="text-lg font-medium text-amber-900 dark:text-amber-200">Wallet Not Connected</h3>
              <p className="text-xs text-amber-700 dark:text-amber-400 mt-1 mb-4">
                Connect your Web3 MetaMask wallet to perform identity verification.
              </p>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                  CONNECTED WALLET ADDRESS
                </label>
                <input
                  type="text"
                  value={account || ''}
                  disabled
                  className="w-full bg-gray-100 dark:bg-slate-800 text-gray-700 dark:text-gray-300 font-mono text-sm px-4 py-3 rounded-xl border border-gray-200 dark:border-slate-700"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                    COMPANY / SME LEGAL NAME *
                  </label>
                  <input
                    type="text"
                    name="companyName"
                    required
                    value={formData.companyName}
                    onChange={handleChange}
                    placeholder="e.g. Apex Global Exports LLC"
                    className="w-full bg-white dark:bg-slate-800 text-gray-900 dark:text-white text-sm px-4 py-3 rounded-xl border border-gray-300 dark:border-slate-700 focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                    BUSINESS TAX / REGISTRATION NO. *
                  </label>
                  <input
                    type="text"
                    name="registrationNumber"
                    required
                    value={formData.registrationNumber}
                    onChange={handleChange}
                    placeholder="e.g. US-TAX-998822"
                    className="w-full bg-white dark:bg-slate-800 text-gray-900 dark:text-white text-sm px-4 py-3 rounded-xl border border-gray-300 dark:border-slate-700 focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1 flex items-center gap-1">
                    <Globe className="h-3.5 w-3.5 text-gray-400" /> COUNTRY OF REGISTRATION
                  </label>
                  <select
                    name="country"
                    value={formData.country}
                    onChange={handleChange}
                    className="w-full bg-white dark:bg-slate-800 text-gray-900 dark:text-white text-sm px-4 py-3 rounded-xl border border-gray-300 dark:border-slate-700 focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="United States">United States</option>
                    <option value="Germany">Germany</option>
                    <option value="United Kingdom">United Kingdom</option>
                    <option value="India">India</option>
                    <option value="Singapore">Singapore</option>
                    <option value="United Arab Emirates">United Arab Emirates</option>
                    <option value="Japan">Japan</option>
                    <option value="Brazil">Brazil</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1 flex items-center gap-1">
                    <FileText className="h-3.5 w-3.5 text-gray-400" /> VERIFICATION DOCUMENT TYPE
                  </label>
                  <select
                    name="idType"
                    value={formData.idType}
                    onChange={handleChange}
                    className="w-full bg-white dark:bg-slate-800 text-gray-900 dark:text-white text-sm px-4 py-3 rounded-xl border border-gray-300 dark:border-slate-700 focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="Business License & Tax ID">Business License & Tax ID</option>
                    <option value="Commercial Register Extract">Commercial Register Extract</option>
                    <option value="Certificate of Incorporation">Certificate of Incorporation</option>
                    <option value="Government Issued Passport">Government Issued Passport</option>
                  </select>
                </div>
              </div>

              {errorMsg && (
                <div className="p-4 bg-red-50 dark:bg-red-950/50 border border-red-200 text-red-700 dark:text-red-300 rounded-xl text-sm">
                  {errorMsg}
                </div>
              )}

              {successMsg && (
                <div className="p-4 bg-emerald-50 dark:bg-emerald-950/50 border border-emerald-200 text-emerald-700 dark:text-emerald-300 rounded-xl text-sm flex items-center gap-2">
                  <CheckCircle2 className="h-5 w-5 text-emerald-500" />
                  {successMsg}
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full py-3.5 px-6 rounded-xl font-semibold text-white bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-700 hover:to-violet-700 shadow-lg transition-all duration-200 disabled:opacity-50"
              >
                {loading ? 'Verifying Identity...' : 'Submit & Complete KYC Verification'}
              </button>
            </form>
          )}
        </div>

        {/* Right Column: Active Status Card */}
        <div className="space-y-6">
          <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 shadow-lg border border-gray-100 dark:border-slate-800">
            <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-emerald-500" />
              KYC Status Badge
            </h3>

            {kycStatus ? (
              <div className="space-y-4">
                <div className="p-4 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 rounded-xl">
                  <div className="flex items-center space-x-2 text-emerald-700 dark:text-emerald-400 font-bold text-sm">
                    <CheckCircle2 className="h-5 w-5 text-emerald-500" />
                    <span>VERIFIED SME IDENTITY</span>
                  </div>
                  <p className="text-xs text-emerald-600 dark:text-emerald-400 mt-1">
                    Verified on: {new Date(kycStatus.verifiedAt).toLocaleDateString()}
                  </p>
                </div>

                <div className="space-y-2 text-sm border-t border-gray-100 dark:border-slate-800 pt-3">
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-500 dark:text-gray-400">Company:</span>
                    <span className="font-semibold text-gray-900 dark:text-white">{kycStatus.companyName}</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-500 dark:text-gray-400">Reg No:</span>
                    <span className="font-mono text-gray-700 dark:text-gray-300">{kycStatus.registrationNumber}</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-500 dark:text-gray-400">Country:</span>
                    <span className="text-gray-900 dark:text-white">{kycStatus.country}</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="p-4 bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 rounded-xl text-center">
                <AlertTriangle className="h-8 w-8 text-amber-500 mx-auto mb-2" />
                <span className="text-xs font-bold text-amber-800 dark:text-amber-300 block">PENDING KYC VERIFICATION</span>
                <p className="text-xs text-amber-700 dark:text-amber-400 mt-1">
                  Complete the verification form on the left to activate full cross-border smart contract escrow privileges.
                </p>
              </div>
            )}
          </div>

          <div className="bg-gradient-to-br from-slate-900 to-indigo-950 text-white rounded-2xl p-6 shadow-lg">
            <h4 className="font-semibold text-sm mb-3 flex items-center gap-2 text-indigo-300">
              <Lock className="h-4 w-4" /> Why KYC is Mandatory
            </h4>
            <ul className="text-xs text-slate-300 space-y-2 list-disc list-inside">
              <li>Enforces global AML (Anti-Money Laundering) smart contract rules.</li>
              <li>Protects buyer & supplier escrows from counterparty fraud.</li>
              <li>Generates verified trust scores for the AI Risk Engine.</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default KYCPage;
