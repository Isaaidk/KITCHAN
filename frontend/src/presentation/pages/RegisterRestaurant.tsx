import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { onboardingService } from '../../infrastructure/services/onboarding.service';

export const RegisterRestaurant: React.FC = () => {
    const navigate = useNavigate();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        setLoading(true); setError(null);
        
        const formData = new FormData(e.currentTarget);
        const requestData = {
            restaurante: {
                nombre_comercial: formData.get('nombre_comercial') as string,
                razon_social: formData.get('razon_social') as string,
                identificacion_fiscal: formData.get('identificacion_fiscal') as string,
                direccion: formData.get('direccion') as string,
                telefono: formData.get('telefono') as string,
                email_corporativo: formData.get('email_corporativo') as string,
            },
            admin: {
                nombre: formData.get('admin_nombre') as string,
                email: formData.get('admin_email') as string,
                password: formData.get('admin_password') as string,
            }
        };

        try {
            await onboardingService.registrarRestaurante(requestData);
            alert("Restaurante registrado con éxito. Ahora puedes iniciar sesión.");
            navigate('/login');
        } catch (err: any) {
            setError(err.response?.data?.detail?.[0]?.msg || 'Error al registrar el restaurante');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{ maxWidth: '600px', margin: '40px auto', padding: '20px', border: '1px solid #ccc', borderRadius: '8px' }}>
            <h2>Registrar Nuevo Restaurante</h2>
            {error && <p style={{ color: 'red', backgroundColor: '#ffe6e6', padding: '10px' }}>{error}</p>}
            
            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
                <fieldset style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    <legend>Datos del Restaurante</legend>
                    <input name="nombre_comercial" placeholder="Nombre Comercial (Ej. KITCHAN Center)" required />
                    <input name="razon_social" placeholder="Razón Social" required />
                    <input name="identificacion_fiscal" placeholder="RUC / Identificación Fiscal" required />
                    <input name="direccion" placeholder="Dirección Matriz" required />
                    <input name="telefono" placeholder="Teléfono" required />
                    <input name="email_corporativo" type="email" placeholder="Email Corporativo" required />
                </fieldset>

                <fieldset style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    <legend>Datos del Administrador Principal</legend>
                    <input name="admin_nombre" placeholder="Nombre Completo" required />
                    <input name="admin_email" type="email" placeholder="Email (ej. isaac.puga@udla.edu.ec)" required />
                    <input name="admin_password" type="password" placeholder="Contraseña de acceso" required />
                </fieldset>

                <button type="submit" disabled={loading} style={{ padding: '10px', backgroundColor: '#0056b3', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
                    {loading ? 'Registrando...' : 'Crear Restaurante'}
                </button>
            </form>
            <p style={{ textAlign: 'center', marginTop: '20px' }}>
                ¿Ya tienes una cuenta? <Link to="/login">Inicia Sesión aquí</Link>
            </p>
        </div>
    );
};