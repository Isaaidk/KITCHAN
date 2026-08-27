import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Login } from '../pages/Login';
import { RegisterRestaurant } from '../pages/RegisterRestaurant';
import { ProtectedRoute } from './ProtectedRoute';
import { AdminDashboard } from '../pages/AdminDashboard'; 

const OperadorDashboard = () => <h2>Panel de Operador (Ruta Protegida)</h2>;

export const AppRouter: React.FC = () => {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/login" element={<Login />} />
                <Route path="/registro" element={<RegisterRestaurant />} />
                
                <Route path="/admin" element={
                    <ProtectedRoute allowedRoles={['ADMIN']}>
                        <AdminDashboard />
                    </ProtectedRoute>
                } />
                
                <Route path="/operador" element={
                    <ProtectedRoute allowedRoles={['OPERADOR']}>
                        <OperadorDashboard />
                    </ProtectedRoute>
                } />

                <Route path="*" element={<Navigate to="/login" replace />} />
            </Routes>
        </BrowserRouter>
    );
};