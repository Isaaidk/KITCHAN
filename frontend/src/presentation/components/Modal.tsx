import React, { type ReactNode } from 'react';

interface ModalProps {
    isOpen: boolean;
    onClose: () => void;
    title: string;
    children: ReactNode;
}

export const Modal: React.FC<ModalProps> = ({ isOpen, onClose, title, children }) => {
    if (!isOpen) return null;

    return (
        <div style={overlayStyle}>
            <div style={modalStyle}>
                <div style={headerStyle}>
                    <h3 style={{ margin: 0 }}>{title}</h3>
                    <button onClick={onClose} style={closeButtonStyle}>✕</button>
                </div>
                <div style={contentStyle}>
                    {children}
                </div>
            </div>
        </div>
    );
};

// Estilos limpios y directos para el UX
const overlayStyle: React.CSSProperties = {
    position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.5)', display: 'flex',
    alignItems: 'center', justifyContent: 'center', zIndex: 1000
};
const modalStyle: React.CSSProperties = {
    backgroundColor: '#fff', borderRadius: '8px', width: '100%',
    maxWidth: '500px', boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
};
const headerStyle: React.CSSProperties = {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    padding: '16px 20px', borderBottom: '1px solid #eee'
};
const contentStyle: React.CSSProperties = { padding: '20px' };
const closeButtonStyle: React.CSSProperties = {
    background: 'none', border: 'none', fontSize: '18px', cursor: 'pointer'
};