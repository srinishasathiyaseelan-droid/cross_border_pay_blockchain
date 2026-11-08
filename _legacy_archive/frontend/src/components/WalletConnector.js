import React from 'react';
import { Wallet, Loader2, LogOut, AlertCircle } from 'lucide-react';
import { useWallet } from '../context/WalletContext';

const WalletConnector = () => {
  const { isConnected, isConnecting, error, connectWallet, disconnectWallet } = useWallet();

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-3 flex items-center space-x-2 max-w-xs">
        <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0" />
        <p className="text-sm text-red-700">{error}</p>
      </div>
    );
  }

  if (isConnected) {
    return (
      <button
        onClick={disconnectWallet}
        className="flex items-center space-x-2 bg-red-50 hover:bg-red-100 text-red-700 font-semibold py-2 px-4 rounded-lg border border-red-200 transition-all duration-200 hover:shadow-md"
      >
        <LogOut className="h-4 w-4" />
        <span>Disconnect</span>
      </button>
    );
  }

  return (
    <button
      onClick={connectWallet}
      disabled={isConnecting}
      className="btn-primary flex items-center space-x-2"
    >
      {isConnecting ? (
        <>
          <Loader2 className="h-5 w-5 animate-spin" />
          <span>Connecting...</span>
        </>
      ) : (
        <>
          <Wallet className="h-5 w-5" />
          <span>Connect Wallet</span>
        </>
      )}
    </button>
  );
};

export default WalletConnector;
