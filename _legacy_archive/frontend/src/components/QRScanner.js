import React, { useEffect, useState, useRef } from 'react';
import { Html5Qrcode } from 'html5-qrcode';
import { AlertCircle } from 'lucide-react';

const QRScanner = ({ onScanSuccess }) => {
    const [error, setError] = useState(null);
    const scannerRef = useRef(null);

    useEffect(() => {
        let isMounted = true;

        const startScanner = async () => {
            try {
                // Ensure media devices are an option
                if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) {
                    if (isMounted) setError('Camera API not supported by this browser.');
                    return;
                }

                // Check for camera presence
                const devices = await navigator.mediaDevices.enumerateDevices();
                const videoDevices = devices.filter(device => device.kind === 'videoinput');
                
                if (videoDevices.length === 0) {
                    if (isMounted) setError('No camera device found on this system.');
                    return;
                }

                const html5QrCode = new Html5Qrcode("reader");
                scannerRef.current = html5QrCode;

                await html5QrCode.start(
                    { facingMode: "environment" },
                    { fps: 10, qrbox: { width: 250, height: 250 } },
                    (decodedText) => {
                        // Stop scanning once we get a success
                        if (html5QrCode.isScanning) {
                            html5QrCode.stop().then(() => {
                                onScanSuccess(decodedText);
                            }).catch(console.error);
                        } else {
                            onScanSuccess(decodedText);
                        }
                    },
                    (errorMessage) => {
                        // ignore noisy scan failures
                    }
                );
            } catch (err) {
                console.error("Camera access error:", err);
                if (isMounted) setError('Camera permission denied or not available. Please allow camera access or use manual input.');
            }
        };

        startScanner();

        return () => {
            isMounted = false;
            // Cleanup on unmount
            if (scannerRef.current && scannerRef.current.isScanning) {
                scannerRef.current.stop().then(() => {
                    scannerRef.current.clear();
                }).catch(console.error);
            }
        };
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    if (error) {
        return (
            <div className="p-4 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg flex flex-col items-center justify-center text-center">
                <AlertCircle className="h-8 w-8 text-red-600 dark:text-red-400 mb-2" />
                <p className="text-sm text-red-800 dark:text-red-300 font-medium">{error}</p>
            </div>
        );
    }

    return (
        <div className="relative w-full max-w-sm mx-auto overflow-hidden rounded-xl bg-gray-900 shadow-xl overflow-y-hidden">
            <div id="reader" className="w-full"></div>
            <div className="absolute inset-0 border-4 border-emerald-500 animate-pulse pointer-events-none rounded-xl" />
        </div>
    );
};

export default QRScanner;
