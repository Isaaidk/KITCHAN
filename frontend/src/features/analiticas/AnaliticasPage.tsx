import { useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import CanalLogo from "../../shared/components/CanalLogo";
import Icon from "../../shared/components/Icon";
import { fechaCorta, horaEtiqueta, minutos, moneda, numero, porcentaje } from "../../shared/utils/formato";
import { infoCanal, nombreMetodoPago } from "../pedidos/estadoUtils";
import compartido from "./Compartido.module.css";
import ExportModal from "./ExportModal";
import {
  COLOR_AMBAR,
  COLOR_BARRA_SUAVE,
  COLOR_EJE,
  COLOR_GRILLA,
  COLOR_PRINCIPAL,
  COLOR_TURQUESA,
  estiloTooltip,
} from "./estilosGraficos";
import RankingProductos from "./RankingProductos";
import SelectorRango from "./SelectorRango";
import type { CanalResumen, DashboardPedidos } from "./types";
import { RANGOS, useDashboard, useRango } from "./useDashboard";
import styles from "./AnaliticasPage.module.css";

const COLORES_PAGO = [COLOR_PRINCIPAL, COLOR_TURQUESA, COLOR_AMBAR, "#2e3a46", "#b4533a", "#5f7d4e"];

/** Frase corta con el canal de mayor demanda y el que más demora. */
function conclusionesCanales(canales: CanalResumen[]) {
  const conTiempo = canales.filter((c) => c.tiempo_promedio_minutos > 0);
  const masDemanda = canales[0];
  const masDemora =
    conTiempo.length > 1
      ? conTiempo.reduce((a, b) => (b.tiempo_promedio_minutos > a.tiempo_promedio_minutos ? b : a))
      : null;
  return { masDemanda, masDemora };
}

function ComparacionCanales({ datos }: { datos: DashboardPedidos }) {
  const { por_canal: canales, umbral_demora_minutos: umbral } = datos;
  const { masDemanda, masDemora } = conclusionesCanales(canales);

  return (
    <section className={`${compartido.panel} ${styles.ancho}`} aria-labelledby="an-canales">
      <div className={compartido.panelCabecera}>
        <div>
          <h2 id="an-canales" className={compartido.panelTitulo}>
            Comparación de canales
          </h2>
          <p className={compartido.panelSub}>
            Pedidos, ventas y tiempos de preparación. Se considera demorado un pedido que pasa de {umbral} min.
          </p>
        </div>
      </div>

      {canales.length === 0 ? (
        <div className={compartido.vacio}>
          <span className={compartido.vacioTitulo}>Sin pedidos en este periodo</span>
          <span>Cuando lleguen pedidos de cualquier canal los verás comparados aquí.</span>
        </div>
      ) : (
        <>
          <ul className={styles.conclusiones}>
            <li>
              <Icon name="rayo" size={15} />
              <span>
                Mayor demanda: <strong>{infoCanal(masDemanda.canal).nombre}</strong> con {porcentaje(masDemanda.porcentaje_pedidos)} de los pedidos
              </span>
            </li>
            {masDemora && (
              <li className={styles.conclusionDemora}>
                <Icon name="reloj" size={15} />
                <span>
                  Más demora: <strong>{infoCanal(masDemora.canal).nombre}</strong> con {minutos(masDemora.tiempo_promedio_minutos)} de promedio
                </span>
              </li>
            )}
          </ul>

          <div className={styles.tablaScroll}>
            <table className="table">
              <caption className="sr-only">Comparación de canales de venta</caption>
              <thead>
                <tr>
                  <th scope="col">Canal</th>
                  <th scope="col">Pedidos</th>
                  <th scope="col" className="table-num">
                    Ventas
                  </th>
                  <th scope="col" className="table-num">
                    Ticket
                  </th>
                  <th scope="col" className="table-num">
                    Tiempo prom.
                  </th>
                  <th scope="col" className="table-num">
                    Demorados
                  </th>
                  <th scope="col" className="table-num">
                    Cancelados
                  </th>
                </tr>
              </thead>
              <tbody>
                {canales.map((c) => {
                  const { nombre, color } = infoCanal(c.canal);
                  const esDemanda = c === masDemanda && canales.length > 1;
                  const esDemora = masDemora?.canal === c.canal;
                  return (
                    <tr key={c.canal}>
                      <td>
                        <div className={styles.canalCelda}>
                          <CanalLogo canal={c.canal} color={color} nombre={nombre} size={30} />
                          <div>
                            <div className={styles.canalNombre}>{nombre}</div>
                            <div className={styles.etiquetas}>
                              {esDemanda && <span className={`${styles.etiqueta} ${styles.etiquetaDemanda}`}>Mayor demanda</span>}
                              {esDemora && <span className={`${styles.etiqueta} ${styles.etiquetaDemora}`}>Más demora</span>}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td>
                        <div className={styles.pedidosCelda}>
                          <strong>{numero(c.pedidos)}</strong>
                          <span className={styles.participacionFondo} aria-hidden="true">
                            <span className={styles.participacionRelleno} style={{ width: `${c.porcentaje_pedidos}%`, background: color }} />
                          </span>
                          <span className={styles.participacionTexto}>{porcentaje(c.porcentaje_pedidos)}</span>
                        </div>
                      </td>
                      <td className="table-num">
                        <strong>{moneda(c.ventas)}</strong>
                        <div className={styles.sub}>{porcentaje(c.porcentaje_ventas)} del total</div>
                      </td>
                      <td className="table-num">{moneda(c.ticket_promedio)}</td>
                      <td className="table-num">{c.tiempo_promedio_minutos > 0 ? minutos(c.tiempo_promedio_minutos) : "—"}</td>
                      <td className="table-num">
                        <span className={c.tasa_demora >= 30 ? styles.alerta : undefined}>
                          {c.tiempo_promedio_minutos > 0 ? porcentaje(c.tasa_demora) : "—"}
                        </span>
                      </td>
                      <td className="table-num">{numero(c.cancelados)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}

function Productos({ datos }: { datos: DashboardPedidos }) {
  return (
    <>
      <div className={compartido.dosColumnas}>
        <section className={compartido.panel} aria-labelledby="an-mas">
          <div className={compartido.panelCabecera}>
            <div>
              <h2 id="an-mas" className={compartido.panelTitulo}>
                Platos más vendidos
              </h2>
              <p className={compartido.panelSub}>Por unidades vendidas</p>
            </div>
          </div>
          <RankingProductos items={datos.productos_mas_vendidos} vacio="Aún no hay ventas en este periodo." />
        </section>

        <section className={compartido.panel} aria-labelledby="an-menos">
          <div className={compartido.panelCabecera}>
            <div>
              <h2 id="an-menos" className={compartido.panelTitulo}>
                Platos menos solicitados
              </h2>
              <p className={compartido.panelSub}>Los que menos salen entre los que sí se vendieron</p>
            </div>
          </div>
          <RankingProductos
            menos
            items={datos.productos_menos_vendidos}
            vacio={
              datos.productos_distintos === 0
                ? "Aún no hay ventas en este periodo."
                : "Hay muy pocos platos distintos para armar este ranking."
            }
          />
        </section>
      </div>

      <section className={`${compartido.panel} ${styles.ancho}`} aria-labelledby="an-combos">
        <div className={compartido.panelCabecera}>
          <div>
            <h2 id="an-combos" className={compartido.panelTitulo}>
              Combos más vendidos
            </h2>
            <p className={compartido.panelSub}>Se reconocen porque su nombre incluye la palabra “combo”</p>
          </div>
        </div>
        <RankingProductos
          items={datos.combos_mas_vendidos}
          vacio="Todavía no hay combos vendidos en este periodo."
        />
      </section>
    </>
  );
}

export function Horarios({ datos }: { datos: DashboardPedidos }) {
  const pico = datos.hora_pico;
  const total = datos.por_hora.reduce((s, p) => s + p.pedidos, 0);
  return (
    <section className={compartido.panel} aria-labelledby="an-horarios">
      <div className={compartido.panelCabecera}>
        <div>
          <h2 id="an-horarios" className={compartido.panelTitulo}>
            Horarios con más pedidos
          </h2>
          <p className={compartido.panelSub}>Hora del local, sin contar cancelados</p>
        </div>
        {pico && (
          <span className={styles.picoChip}>
            <Icon name="rayo" size={13} />
            Hora pico {horaEtiqueta(pico.hora)} · {numero(pico.pedidos)} pedidos
          </span>
        )}
      </div>
      {total === 0 ? (
        <div className={compartido.vacio}>
          <span>Aún no hay pedidos en este periodo.</span>
        </div>
      ) : (
        <div role="img" aria-label={`Pedidos por hora. Hora pico ${pico ? horaEtiqueta(pico.hora) : "sin datos"}`}>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={datos.por_hora} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={COLOR_GRILLA} vertical={false} />
              <XAxis
                dataKey="hora"
                fontSize={11}
                tickLine={false}
                axisLine={false}
                stroke={COLOR_EJE}
                interval={2}
                tickFormatter={(h: number) => `${h}h`}
              />
              <YAxis allowDecimals={false} fontSize={11} tickLine={false} axisLine={false} stroke={COLOR_EJE} />
              <Tooltip
                {...estiloTooltip}
                labelFormatter={(h: number) => horaEtiqueta(h)}
                formatter={(v: number) => [v, "Pedidos"]}
              />
              <Bar dataKey="pedidos" radius={[5, 5, 0, 0]} maxBarSize={22} animationDuration={800}>
                {datos.por_hora.map((p) => (
                  <Cell key={p.hora} fill={pico && p.hora === pico.hora ? COLOR_PRINCIPAL : COLOR_BARRA_SUAVE} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  );
}

export function Clientes({ datos }: { datos: DashboardPedidos }) {
  const c = datos.clientes;
  const maximo = Math.max(...c.distribucion.map((d) => d.clientes), 1);
  return (
    <section className={compartido.panel} aria-labelledby="an-clientes">
      <div className={compartido.panelCabecera}>
        <div>
          <h2 id="an-clientes" className={compartido.panelTitulo}>
            Frecuencia de compra
          </h2>
          <p className={compartido.panelSub}>Aproximada: se agrupa por el nombre del cliente</p>
        </div>
      </div>
      {c.clientes_unicos === 0 ? (
        <div className={compartido.vacio}>
          <span>Aún no hay clientes en este periodo.</span>
        </div>
      ) : (
        <>
          <dl className={styles.estadisticas}>
            <div>
              <dt>Clientes</dt>
              <dd>{numero(c.clientes_unicos)}</dd>
            </div>
            <div>
              <dt>Recurrentes</dt>
              <dd>
                {numero(c.clientes_recurrentes)} <small>({porcentaje(c.tasa_recurrencia)})</small>
              </dd>
            </div>
            <div>
              <dt>Pedidos por cliente</dt>
              <dd>{numero(c.pedidos_por_cliente, 1)}</dd>
            </div>
          </dl>

          <ul className={styles.distribucion} aria-label="Clientes según cuántas veces compraron">
            {c.distribucion.map((d) => (
              <li key={d.etiqueta}>
                <span className={styles.distribucionEtiqueta}>{d.etiqueta}</span>
                <span className={styles.distribucionFondo} aria-hidden="true">
                  <span className={styles.distribucionRelleno} style={{ width: `${(d.clientes / maximo) * 100}%` }} />
                </span>
                <span className={styles.distribucionNumero}>{numero(d.clientes)}</span>
              </li>
            ))}
          </ul>

          {c.mas_frecuentes.length > 0 && (
            <>
              <h3 className={styles.subtitulo}>Clientes más frecuentes</h3>
              <ul className={styles.frecuentes}>
                {c.mas_frecuentes.map((f) => (
                  <li key={f.cliente}>
                    <span className={styles.frecuenteNombre}>{f.cliente}</span>
                    <span className={styles.frecuenteCifras}>
                      {numero(f.pedidos)} pedidos · {moneda(f.ventas)}
                    </span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </>
      )}
    </section>
  );
}

export function MetodosPago({ datos }: { datos: DashboardPedidos }) {
  const pagos = datos.metodos_pago;
  return (
    <section className={`${compartido.panel} ${styles.ancho}`} aria-labelledby="an-pagos">
      <div className={compartido.panelCabecera}>
        <div>
          <h2 id="an-pagos" className={compartido.panelTitulo}>
            Métodos de pago
          </h2>
          <p className={compartido.panelSub}>Cuáles se usan más y cuánto pesan en las ventas</p>
        </div>
      </div>

      {!pagos.disponible ? (
        <div className={compartido.vacio}>
          <Icon name="dinero" size={22} />
          <span className={compartido.vacioTitulo}>Aún no hay datos de pago</span>
          <span>
            Ningún pedido de este periodo trae el método de pago. Cuando los canales lo informen verás aquí el
            desglose y su peso en las ventas.
          </span>
        </div>
      ) : (
        <div className={styles.pagos}>
          <div role="img" aria-label={`Ventas por método de pago: ${pagos.items.map((i) => `${nombreMetodoPago(i.metodo)} ${porcentaje(i.porcentaje_ventas)}`).join(", ")}`}>
            <ResponsiveContainer width={210} height={210}>
              <PieChart>
                <Pie
                  data={pagos.items}
                  dataKey="ventas"
                  nameKey="metodo"
                  innerRadius={62}
                  outerRadius={96}
                  paddingAngle={2}
                  animationDuration={800}
                >
                  {pagos.items.map((_, i) => (
                    <Cell key={i} fill={COLORES_PAGO[i % COLORES_PAGO.length]} />
                  ))}
                </Pie>
                <Tooltip
                  {...estiloTooltip}
                  formatter={(v: number, _n: string, p: { payload?: { metodo: string } }) => [
                    moneda(v),
                    nombreMetodoPago(p.payload?.metodo ?? ""),
                  ]}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className={styles.tablaScroll}>
            <table className="table">
              <caption className="sr-only">Ventas por método de pago</caption>
              <thead>
                <tr>
                  <th scope="col">Método</th>
                  <th scope="col" className="table-num">
                    Pedidos
                  </th>
                  <th scope="col" className="table-num">
                    Ventas
                  </th>
                  <th scope="col" className="table-num">
                    % de las ventas
                  </th>
                </tr>
              </thead>
              <tbody>
                {pagos.items.map((p, i) => (
                  <tr key={p.metodo}>
                    <td>
                      <span className={styles.metodo}>
                        <span className={styles.metodoPunto} style={{ background: COLORES_PAGO[i % COLORES_PAGO.length] }} aria-hidden="true" />
                        {nombreMetodoPago(p.metodo)}
                      </span>
                    </td>
                    <td className="table-num">{numero(p.pedidos)}</td>
                    <td className="table-num">
                      <strong>{moneda(p.ventas)}</strong>
                    </td>
                    <td className="table-num">{porcentaje(p.porcentaje_ventas)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {pagos.sin_dato > 0 && (
              <p className={styles.nota}>
                {numero(pagos.sin_dato)} {pagos.sin_dato === 1 ? "pedido no informó" : "pedidos no informaron"} su método
                de pago; el desglose cubre el {porcentaje(pagos.cobertura)} de los pedidos.
              </p>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

export default function AnaliticasPage() {
  const [rango, setRango] = useRango();
  const { datos, cargando, error, reintentar } = useDashboard(rango);
  const [mostrarExport, setMostrarExport] = useState(false);
  const descripcion = RANGOS.find((r) => r.valor === rango)?.descripcion ?? "";

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Analíticas</h1>
          <p className="page-subtitle" aria-live="polite">
            Detalle de {descripcion}
            {datos && datos.rango !== "hoy" ? ` · del ${fechaCorta(datos.desde)} al ${fechaCorta(datos.hasta)}` : ""}
          </p>
        </div>
        <div className={styles.acciones}>
          <SelectorRango valor={rango} onCambio={setRango} />
          <button className="btn btn-primary" onClick={() => setMostrarExport(true)} disabled={!datos}>
            <Icon name="descargar" size={16} />
            Exportar
          </button>
        </div>
      </div>

      {error && (
        <div className={`alert alert-error ${compartido.errorAnaliticas}`} role="alert">
          <Icon name="alerta" size={16} />
          <span className={compartido.errorTexto}>
            No se pudieron cargar las analíticas. Revisa la conexión e inténtalo de nuevo.
          </span>
          <button type="button" className="btn btn-secondary btn-sm" onClick={reintentar}>
            <Icon name="sync" size={14} />
            Reintentar
          </button>
        </div>
      )}

      {!datos && !error && (
        <div className={compartido.panel} aria-busy="true">
          <div className="skeleton" style={{ height: 14, width: "30%", marginBottom: 20 }} />
          <div className="skeleton" style={{ height: 220 }} />
          <span className="sr-only" role="status">
            Cargando las analíticas…
          </span>
        </div>
      )}

      {datos && (
        <div className={`${styles.secciones} ${cargando ? styles.actualizando : ""}`} aria-busy={cargando}>
          <ComparacionCanales datos={datos} />
          <Productos datos={datos} />
          <div className={compartido.dosColumnas}>
            <Horarios datos={datos} />
            <Clientes datos={datos} />
          </div>
          <MetodosPago datos={datos} />
        </div>
      )}

      {mostrarExport && datos && <ExportModal datos={datos} onClose={() => setMostrarExport(false)} />}
    </div>
  );
}
