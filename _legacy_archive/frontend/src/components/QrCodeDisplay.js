import React, { useState, useEffect } from 'react';
import QRCode from 'qrcode';

const QrCodeDisplay = ({ data, size = 128 }) => {
    const [src, setSrc] = useState('');

    useEffect(() => {
        if (!data) return;
        QRCode.toDataURL(data, { width: size, margin: 1 })
            .then(setSrc)
            .catch(err => console.error(err));
    }, [data, size]);

    if (!src) return <div className="animate-pulse bg-gray-200 rounded" style={{ width: size, height: size }}></div>;

    return <img src={src} alt="QR Code" className="border rounded p-1 bg-white shadow-sm" style={{ width: size, height: size }} />;
};

export default QrCodeDisplay;
