import { useEffect, useState } from "react";
import { mensajeDeError } from "../../shared/api/mensajeDeError";
import { useToastStore } from "../../shared/stores/toastStore";
import { facturarPedido, obtenerFactura, type Factura } from "./facturacionApi";

/**
 * Factura electrónica de un pedido. KITCHAN la emite en Odoo y Odoo la envía
 * al SRI; el estado se actualiza por el webhook de Odoo o la conciliación.
 */
export function useFacturaPedido(pedidoId: string) {
  const [factura, setFactura] = useState<Factura | null>(null);
  const [cargando, setCargando] = useState(true);
  const [facturando, setFacturando] = useState(false);

  useEffect(() => {
    let vigente = true;
    setCargando(true);
    obtenerFactura(pedidoId)
      .then((datos) => vigente && setFactura(datos))
      .catch(() => vigente && setFactura(null))
      .finally(() => vigente && setCargando(false));
    return () => {
      vigente = false;
    };
  }, [pedidoId]);

  const facturar = async () => {
    setFacturando(true);
    try {
      setFactura(await facturarPedido(pedidoId));
    } catch (err) {
      useToastStore
        .getState()
        .add(mensajeDeError(err, "No se pudo emitir la factura."), "critica");
    } finally {
      setFacturando(false);
    }
  };

  return { factura, cargando, facturando, facturar };
}
