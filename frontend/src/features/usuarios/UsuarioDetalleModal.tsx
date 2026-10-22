import { useState } from "react";
import CanalLogo from "../../shared/components/CanalLogo";
import Icon from "../../shared/components/Icon";
import Modal from "../../shared/components/Modal";
import type { Usuario } from "../../shared/types/usuario";
import { fechaHora, hace, minutos, moneda, numero, porcentaje } from "../../shared/utils/formato";
import SelectorRango from "../analiticas/SelectorRango";
import type { Rango } from "../analiticas/types";
import { RANGOS } from "../analiticas/useDashboard";
import { ETIQUETA_ESTADO, infoCanal } from "../pedidos/estadoUtils";
import { useActividad } from "./actividad";
import { ETIQUETA_ROL, iniciales, tonoPara } from "./usuariosUtils";
import styles from "./UsuarioDetalleModal.module.css";

interface Props {
  usuario: Usuario;
  esYo: boolean;
  onClose: () => void;
  onEditar: () => void;
  onEnviarCodigo: () => void;
}

/** Ficha de una persona del equipo: sus datos y qué pedidos ha atendido. */
export default function UsuarioDetalleModal({ usuario, esYo, onClose, onEditar, onEnviarCodigo }: Props) {
  const [rango, setRango] = useState<Rango>("7d");
  const { datos, error, cargando } = useActividad(rango, usuario.id);
  const detalle = datos?.detalle ?? null;
  const descripcion = RANGOS.find((r) => r.valor === rango)?.descripcion ?? "";
  const maxCanal = Math.max(...(detalle?.por_canal.map((c) => c.pedidos) ?? [1]), 1);

  return (
    <Modal titulo={`Ficha de ${usuario.nombre}`} onClose={onClose} ancho={600}>
      <div className={styles.cabecera}>
        <div
          className={`${styles.avatar} ${usuario.estado ? "" : styles.avatarInactivo}`}
          style={{ ["--tono" as string]: tonoPara(usuario.nombre) }}
        >
          {iniciales(usuario.nombre)}
        </div>
        <div className={styles.cabeceraTexto}>
          <div className={styles.nombre}>
            {usuario.nombre}
            {esYo && <span className={styles.tu}>Tú</span>}
          </div>
          <div className={styles.email}>{usuario.email}</div>
          <div className={styles.etiquetas}>
            <span className={`${styles.rol} ${usuario.rol === "ADMIN" ? styles.rolAdmin : styles.rolOperador}`}>
              <Icon name={usuario.rol === "ADMIN" ? "escudo" : "cola"} size={13} />
              {ETIQUETA_ROL[usuario.rol]}
            </span>
            <span className={`${styles.estado} ${usuario.estado ? styles.estadoActivo : ""}`}>
              {usuario.estado ? "Activo" : "Inactivo"}
            </span>
          </div>
        </div>
      </div>

      <dl className={styles.datos}>
        <div>
          <dt>Alta en el equipo</dt>
          <dd>{usuario.creado_en ? fechaHora(usuario.creado_en) : "—"}</dd>
        </div>
        <div>
          <dt>Último acceso</dt>
          <dd>{usuario.ultimo_acceso ? hace(usuario.ultimo_acceso) : "Todavía no ha entrado"}</dd>
        </div>
      </dl>

      <div className={styles.actividadCabecera}>
        <h3 className={styles.subtitulo}>Actividad en cocina</h3>
        <SelectorRango valor={rango} onCambio={setRango} />
      </div>

      {error && (
        <div className="alert alert-error" role="alert">
          <Icon name="alerta" size={16} />
          No se pudo cargar la actividad. Inténtalo de nuevo más tarde.
        </div>
      )}

      {cargando && (
        <div aria-busy="true">
          <div className="skeleton" style={{ height: 70, marginBottom: 12 }} />
          <div className="skeleton" style={{ height: 120 }} />
          <span className="sr-only" role="status">
            Cargando la actividad…
          </span>
        </div>
      )}

      {detalle && detalle.pedidos_atendidos === 0 && (
        <div className={styles.vacio}>
          <span className={styles.vacioTitulo}>Sin pedidos aceptados en {descripcion}</span>
          <span>
            Aquí se cuentan los pedidos que esta persona acepta desde KITCHAN. Los aceptados antes de que se
            registrara quién los aceptó no se le atribuyen.
          </span>
        </div>
      )}

      {detalle && detalle.pedidos_atendidos > 0 && (
        <>
          <dl className={styles.kpis}>
            <div>
              <dt>Pedidos aceptados</dt>
              <dd>{numero(detalle.pedidos_atendidos)}</dd>
            </div>
            <div>
              <dt>Preparación</dt>
              <dd>{detalle.tiempo_promedio_minutos > 0 ? minutos(detalle.tiempo_promedio_minutos) : "—"}</dd>
            </div>
            <div>
              <dt>Demorados</dt>
              <dd>{detalle.tiempo_promedio_minutos > 0 ? porcentaje(detalle.tasa_demora) : "—"}</dd>
            </div>
            <div>
              <dt>Ventas</dt>
              <dd>{moneda(detalle.ventas)}</dd>
            </div>
          </dl>

          <h3 className={styles.subtitulo}>Por canal</h3>
          <ul className={styles.canales}>
            {detalle.por_canal.map((c) => {
              const { nombre, color } = infoCanal(c.canal);
              return (
                <li key={c.canal}>
                  <CanalLogo canal={c.canal} color={color} nombre={nombre} size={26} />
                  <span className={styles.canalNombre}>{nombre}</span>
                  <span className={styles.barraFondo} aria-hidden="true">
                    <span className={styles.barra} style={{ width: `${(c.pedidos / maxCanal) * 100}%`, background: color }} />
                  </span>
                  <span className={styles.canalNumero}>{numero(c.pedidos)}</span>
                </li>
              );
            })}
          </ul>

          <h3 className={styles.subtitulo}>Últimos pedidos</h3>
          <ul className={styles.recientes}>
            {detalle.recientes.map((r, i) => {
              const { nombre, color } = infoCanal(r.canal);
              return (
                <li key={`${r.fecha}-${i}`}>
                  <CanalLogo canal={r.canal} color={color} nombre={nombre} size={24} />
                  <div className={styles.recienteDatos}>
                    <span className={styles.recienteCliente}>{r.cliente || "Sin nombre"}</span>
                    <span className={styles.recienteSub}>
                      {fechaHora(r.fecha)} · {ETIQUETA_ESTADO[r.estado as keyof typeof ETIQUETA_ESTADO] ?? r.estado}
                      {r.minutos_preparacion !== null && ` · ${minutos(r.minutos_preparacion)}`}
                    </span>
                  </div>
                  <span className={styles.recienteTotal}>{moneda(r.total)}</span>
                </li>
              );
            })}
          </ul>
        </>
      )}

      <div className={styles.acciones}>
        <button type="button" className="btn btn-secondary" onClick={onEnviarCodigo} disabled={!usuario.estado}>
          <Icon name="correo" size={16} />
          Enviar código de acceso
        </button>
        <button type="button" className="btn btn-primary" onClick={onEditar}>
          <Icon name="editar" size={16} />
          Editar
        </button>
      </div>
    </Modal>
  );
}
