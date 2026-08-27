// src/App.tsx
import React from 'react';
import { AuthProvider } from './application/context/AuthContext';
import { AppRouter } from './presentation/router/AppRouter';

const App: React.FC = () => {
    return (
        <AuthProvider>
            <AppRouter />
        </AuthProvider>
    );
};

export default App;