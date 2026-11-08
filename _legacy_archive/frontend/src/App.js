import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { WalletProvider } from './context/WalletContext';
import Navbar from './components/Navbar';
import Home from './pages/Home';
import CreatePayment from './pages/CreatePayment';
import PaymentsPage from './pages/PaymentsPage';
import BlockchainPage from './pages/BlockchainPage';
import DocumentsPage from './pages/DocumentsPage';
import EscrowPage from './pages/EscrowPage';
import Dashboard from './pages/Dashboard';
import RiskMonitoring from './pages/RiskMonitoring';
import AdminPage from './pages/AdminPage';
import SettingsPage from './pages/SettingsPage';
import KYCPage from './pages/KYCPage';

function App() {
  return (
    <WalletProvider>
      <Router>
        <div className="min-h-screen w-full overflow-x-hidden bg-gradient-to-br from-gray-50 via-indigo-50 to-violet-50 dark:from-slate-900 dark:via-slate-900 dark:to-slate-800">
          <Navbar />
          <main className="pb-8">
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/kyc" element={<KYCPage />} />
              <Route path="/create-payment" element={<CreatePayment />} />
              <Route path="/payments" element={<PaymentsPage />} />
              <Route path="/blockchain" element={<BlockchainPage />} />
              <Route path="/documents" element={<DocumentsPage />} />
              <Route path="/escrow" element={<EscrowPage />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/risk" element={<RiskMonitoring />} />
              <Route path="/admin" element={<AdminPage />} />
              <Route path="/settings" element={<SettingsPage />} />
              {/* Legacy redirects */}
              <Route path="/pds" element={<Navigate to="/dashboard" replace />} />
              <Route path="/add-event" element={<Navigate to="/create-payment" replace />} />
              <Route path="/create-batch" element={<Navigate to="/create-payment" replace />} />
              <Route path="/batches" element={<Navigate to="/payments" replace />} />
              <Route path="/timeline" element={<Navigate to="/blockchain" replace />} />
              <Route path="/verify" element={<Navigate to="/documents" replace />} />
              <Route path="/lineage" element={<Navigate to="/escrow" replace />} />
            </Routes>
          </main>
        </div>
      </Router>
    </WalletProvider>
  );
}

export default App;
