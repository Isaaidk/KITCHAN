import { WS_URL } from "../api/httpClient";

export function crearSocketPedidos(token: string): WebSocket {
  return new WebSocket(`${WS_URL}/api/v1/pedidos/ws/pedidos?token=${token}`);
}
