import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Globe, PlusCircle, CreditCard, Clock, FileText, Lock, BarChart3, Menu, X, Sun, Moon, Shield, Settings, UserCheck } from 'lucide-react';
import { useWallet } from '../context/WalletContext';
import WalletConnector from './WalletConnector';
import SystemStatus from './SystemStatus';

const Navbar = () => {
  const location = useLocation();
  const { isConnected, account } = useWallet();
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false);

  const [theme, setTheme] = React.useState(() => {
    if (localStorage.theme === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) return 'dark';
    return 'light';
  });

  React.useEffect(() => {
    if (theme === 'dark') { document.documentElement.classList.add('dark'); localStorage.setItem('theme', 'dark'); }
    else { document.documentElement.classList.remove('dark'); localStorage.setItem('theme', 'light'); }
  }, [theme]);

  const toggleTheme = () => setTheme(theme === 'dark' ? 'light' : 'dark');

  const navItems = [
    { path: '/', label: 'Home', icon: Globe },
    { path: '/dashboard', label: 'Dashboard', icon: BarChart3 },
    { path: '/kyc', label: 'KYC', icon: UserCheck },
    { path: '/create-payment', label: 'Create Payment', icon: PlusCircle },
    { path: '/payments', label: 'Payments', icon: CreditCard },
    { path: '/escrow', label: 'Escrow', icon: Lock },
    { path: '/documents', label: 'Documents', icon: FileText },
    { path: '/risk', label: 'Risk', icon: Shield },
    { path: '/blockchain', label: 'Blockchain', icon: Clock },
    { path: '/admin', label: 'Admin', icon: Settings },
  ];

  return (
    <div className="flex flex-col sticky top-0 z-50">
      {/* Top Status Bar */}
      <div className="hidden md:flex bg-gray-50 dark:bg-slate-950 border-b border-gray-200 dark:border-slate-800 h-10 px-4 items-center justify-end text-xs transition-colors duration-200">
        <div className="flex items-center space-x-6">
          <SystemStatus />
          <div className="flex items-center space-x-4 pl-6 border-l border-gray-200 dark:border-slate-800">
            {isConnected && account ? (
              <div className="flex items-center space-x-2 text-green-700 dark:text-green-400 font-mono">
                <div className="h-1.5 w-1.5 bg-green-500 rounded-full animate-pulse"></div>
                <span>{`${account.slice(0, 6)}...${account.slice(-4)}`}</span>
              </div>
            ) : <span className="text-gray-500 dark:text-gray-400">Wallet not connected</span>}
          </div>
        </div>
      </div>

      <nav className="bg-white dark:bg-slate-900 shadow-lg border-b border-gray-200 dark:border-slate-800 transition-colors duration-200 relative">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* Logo */}
            <Link to="/" className="flex items-center space-x-2 group">
              <div className="bg-gradient-to-r from-indigo-600 to-violet-600 p-2 rounded-lg group-hover:scale-110 transition-transform">
                <Globe className="h-6 w-6 text-white" />
              </div>
              <span className="text-2xl font-bold bg-gradient-to-r from-indigo-600 to-violet-600 bg-clip-text text-transparent whitespace-nowrap">CrossPay</span>
            </Link>

            {/* Desktop Navigation */}
            <div className="hidden xl:flex items-center space-x-1">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname === item.path;
                return (
                  <Link key={item.path} to={item.path}
                    className={`flex items-center space-x-2 px-3 py-2 rounded-lg transition-all duration-200 ${
                      isActive ? 'bg-gradient-to-r from-indigo-600 to-violet-600 text-white shadow-lg' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-800'
                    }`}>
                    <Icon className="h-4 w-4" /><span className="font-medium text-sm whitespace-nowrap">{item.label}</span>
                  </Link>
                );
              })}
            </div>

            {/* Right Side */}
            <div className="hidden md:flex items-center space-x-3">
              <button onClick={toggleTheme} className="p-2 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-800 transition-colors" aria-label="Toggle Dark Mode">
                {theme === 'dark' ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
              </button>
              <WalletConnector />
            </div>

            {/* Mobile menu button */}
            <button onClick={() => setMobileMenuOpen(!mobileMenuOpen)} className="xl:hidden p-2 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-800">
              {mobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
            </button>
          </div>

          {/* Mobile Navigation */}
          {mobileMenuOpen && (
            <div className="xl:hidden py-4 space-y-2 border-t border-gray-200 dark:border-slate-700">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname === item.path;
                return (
                  <Link key={item.path} to={item.path} onClick={() => setMobileMenuOpen(false)}
                    className={`flex items-center space-x-3 px-4 py-3 rounded-lg transition-all ${
                      isActive ? 'bg-gradient-to-r from-indigo-600 to-violet-600 text-white' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-800'
                    }`}>
                    <Icon className="h-5 w-5" /><span className="font-medium">{item.label}</span>
                  </Link>
                );
              })}
              <div className="px-4 py-2 flex items-center justify-between border-t border-gray-200 dark:border-slate-700 mt-2 pt-4">
                <span className="text-gray-700 dark:text-gray-300 font-medium">Theme</span>
                <button onClick={toggleTheme} className="p-2 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-800 transition-colors">
                  {theme === 'dark' ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
                </button>
              </div>
              <div className="pt-4 border-t border-gray-200 dark:border-slate-700">
                <div className="px-4"><WalletConnector /></div>
              </div>
            </div>
          )}
        </div>
      </nav>
    </div>
  );
};

export default Navbar;
