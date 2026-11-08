import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Package, RefreshCw, Plus } from 'lucide-react';

const API_BASE_URL = 'http://localhost:4000';

const ShopInventory = () => {
    const [stock, setStock] = useState({});
    const [loading, setLoading] = useState(false);

    // Refill Modal State
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [selectedShop, setSelectedShop] = useState('');
    const [selectedCommodity, setSelectedCommodity] = useState('rice');
    const [refillQuantity, setRefillQuantity] = useState(100);
    const [refillLoading, setRefillLoading] = useState(false);

    useEffect(() => {
        fetchStock();
    }, []);

    const fetchStock = async () => {
        setLoading(true);
        try {
            const res = await axios.get(`${API_BASE_URL}/pds/stock`);
            setStock(res.data);
        } catch (err) {
            console.error("Failed to fetch stock", err);
        } finally {
            setLoading(false);
        }
    };

    const handleOpenRefill = (shopId) => {
        setSelectedShop(shopId);
        setIsModalOpen(true);
    };

    const handleRefillSubmit = async (e) => {
        e.preventDefault();
        setRefillLoading(true);
        try {
            await axios.post(`${API_BASE_URL}/pds/refill`, {
                shopId: selectedShop,
                commodity: selectedCommodity,
                quantity: Number(refillQuantity)
            });
            setIsModalOpen(false);
            fetchStock(); // Refresh
        } catch (err) {
            alert("Refill Failed: " + (err.response?.data?.message || err.message));
        } finally {
            setRefillLoading(false);
        }
    };

    return (
        <div className="bg-white dark:bg-slate-800 p-6 rounded-lg shadow-lg border-l-4 border-purple-500">
            <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-bold flex items-center text-gray-800 dark:text-white">
                    <Package className="mr-2 h-6 w-6" /> Shop Inventory Management
                </h2>
                <button onClick={fetchStock} className="text-gray-500 hover:text-blue-500">
                    <RefreshCw className={`h-5 w-5 ${loading ? 'animate-spin' : ''}`} />
                </button>
            </div>

            <div className="overflow-x-auto">
                <table className="min-w-full text-sm text-left">
                    <thead className="bg-gray-100 dark:bg-slate-700">
                        <tr>
                            <th className="p-3 font-semibold text-gray-700 dark:text-gray-200">Shop ID</th>
                            <th className="p-3 font-semibold text-gray-700 dark:text-gray-200">Rice (kg)</th>
                            <th className="p-3 font-semibold text-gray-700 dark:text-gray-200">Wheat (kg)</th>
                            <th className="p-3 font-semibold text-gray-700 dark:text-gray-200">Sugar (kg)</th>
                            <th className="p-3 font-semibold text-gray-700 dark:text-gray-200">Actions</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                        {Object.entries(stock).map(([shopId, data]) => (
                            <tr key={shopId} className="hover:bg-gray-50 dark:hover:bg-slate-700 transition">
                                <td className="p-3 font-mono font-medium text-gray-800 dark:text-gray-300">{shopId}</td>
                                <td className={`p-3 ${data.rice < 100 ? 'text-red-600 font-bold' : ''}`}>{data.rice}</td>
                                <td className={`p-3 ${data.wheat < 100 ? 'text-red-600 font-bold' : ''}`}>{data.wheat}</td>
                                <td className={`p-3 ${data.sugar < 50 ? 'text-red-600 font-bold' : ''}`}>{data.sugar}</td>
                                <td className="p-3">
                                    <button
                                        onClick={() => handleOpenRefill(shopId)}
                                        className="bg-indigo-100 hover:bg-indigo-200 text-indigo-700 dark:bg-indigo-900 dark:text-indigo-200 px-3 py-1 rounded-full text-xs font-semibold flex items-center"
                                    >
                                        <Plus className="h-3 w-3 mr-1" /> Refill
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Refill Modal */}
            {isModalOpen && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50 animate-fade-in">
                    <div className="bg-white dark:bg-slate-800 rounded-lg shadow-xl w-full max-w-md p-6">
                        <h3 className="text-lg font-bold mb-4 text-gray-800 dark:text-white">Refill Stock for {selectedShop}</h3>
                        <form onSubmit={handleRefillSubmit} className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Commodity</label>
                                <select
                                    className="input-field mt-1 dark:bg-slate-700 dark:text-white"
                                    value={selectedCommodity}
                                    onChange={(e) => setSelectedCommodity(e.target.value)}
                                >
                                    <option value="rice">Rice</option>
                                    <option value="wheat">Wheat</option>
                                    <option value="sugar">Sugar</option>
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Quantity to Add (kg)</label>
                                <input
                                    type="number"
                                    className="input-field mt-1 dark:bg-slate-700 dark:text-white"
                                    value={refillQuantity}
                                    onChange={(e) => setRefillQuantity(e.target.value)}
                                    min="1"
                                    required
                                />
                            </div>
                            <div className="flex justify-end space-x-3 pt-2">
                                <button
                                    type="button"
                                    onClick={() => setIsModalOpen(false)}
                                    className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300 dark:bg-slate-600 dark:text-gray-300"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700 flex items-center"
                                    disabled={refillLoading}
                                >
                                    {refillLoading ? 'Processing...' : 'Add Stock'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ShopInventory;
