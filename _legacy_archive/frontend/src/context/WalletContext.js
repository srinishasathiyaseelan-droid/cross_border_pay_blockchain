import React, { createContext, useContext, useState, useEffect } from 'react';
import { ethers } from 'ethers';

const WalletContext = createContext();

export const useWallet = () => {
  const context = useContext(WalletContext);
  if (!context) {
    throw new Error('useWallet must be used within a WalletProvider');
  }
  return context;
};

export const WalletProvider = ({ children }) => {
  const [account, setAccount] = useState(null);
  const [provider, setProvider] = useState(null);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState(null);

  // Check if wallet is already connected
  useEffect(() => {
    checkWalletConnection();
    
    // Listen for account changes
    if (window.ethereum) {
      window.ethereum.on('accountsChanged', handleAccountsChanged);
      window.ethereum.on('chainChanged', () => {
        window.location.reload();
      });
    }

    return () => {
      if (window.ethereum) {
        window.ethereum.removeListener('accountsChanged', handleAccountsChanged);
      }
    };
  }, []);

  const checkWalletConnection = async () => {
    if (window.ethereum) {
      try {
        const accounts = await window.ethereum.request({ method: 'eth_accounts' });
        if (accounts.length > 0) {
          const provider = new ethers.BrowserProvider(window.ethereum);
          setProvider(provider);
          setAccount(accounts[0]);
        }
      } catch (err) {
        console.error('Error checking wallet connection:', err);
      }
    }
  };

  const handleAccountsChanged = (accounts) => {
    if (accounts.length === 0) {
      setAccount(null);
      setProvider(null);
    } else {
      setAccount(accounts[0]);
    }
  };

  const connectWallet = async () => {
    setIsConnecting(true);
    setError(null);

    if (window.ethereum) {
      try {
        const accounts = await window.ethereum.request({
          method: 'eth_requestAccounts',
        });

        if (accounts.length > 0) {
          const provider = new ethers.BrowserProvider(window.ethereum);
          setProvider(provider);
          setAccount(accounts[0]);
        }
      } catch (err) {
        console.error('Error connecting MetaMask:', err);
        setError(err.message || 'Failed to connect wallet');
      } finally {
        setIsConnecting(false);
      }
    } else {
      // Fallback: Connect Demo Local Hardhat Wallet
      try {
        const demoProvider = new ethers.JsonRpcProvider('http://127.0.0.1:8545');
        const demoAccount = '0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266';
        setProvider(demoProvider);
        setAccount(demoAccount);
        console.log('Connected to Local Hardhat Demo Wallet:', demoAccount);
      } catch (fallbackErr) {
        setError('Could not connect to local demo node.');
      } finally {
        setIsConnecting(false);
      }
    }
  };

  const disconnectWallet = () => {
    setAccount(null);
    setProvider(null);
    setError(null);
  };

  const value = {
    account,
    provider,
    isConnecting,
    error,
    connectWallet,
    disconnectWallet,
    isConnected: !!account,
  };

  return (
    <WalletContext.Provider value={value}>
      {children}
    </WalletContext.Provider>
  );
};
