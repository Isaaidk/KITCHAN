"""Módulo Notificaciones: entrega en tiempo real de los eventos de pedidos.

Implementa el puerto de salida `NotificadorEventosPort` que define `pedidos`
(publicando en Redis pub/sub) y expone el canal WebSocket por el que el KDS
recibe esos eventos. `pedidos` no conoce Redis ni WebSockets: solo su puerto.
"""
