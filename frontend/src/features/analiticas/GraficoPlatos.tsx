import { useState } from "react";
import { Cell, Pie, PieChart, PolarAngleAxis, RadialBar, RadialBarChart, ResponsiveContainer, Tooltip } from "recharts";
import { moneda, numero, porcentaje } from "../../shared/utils/formato";
import { useGraficos } from "./estilosGraficos";
import type { ProductoVendido } from "./types";
import compartido from "./Compartido.module.css";
import styles from "./GraficoPlatos.module.css";

interface Props {
  items: ProductoVendido[];
  /** "donut": porciones de un círculo; "radial": anillos concéntricos, uno por plato. */
  variante?: "donut" | "radial";
  /** Qué se mide: unidades vendidas o lo que facturó cada plato. */
  medida?: "unidades" | "ventas";
  /** Texto cuando todavía no hay ventas que mostrar. */
  vacio: string;
}

const TAMANO = 196;

/**
 * Platos como gráfico circular (porciones o anillos) con su leyenda al lado. La leyenda es la
 * lectura exacta (nombre, cifras y porcentaje); al pasar el cursor por una fila o una porción
 * se resalta la correspondiente.
 */
export default function GraficoPlatos({ items, variante = "donut", medida = "unidades", vacio }: Props) {
  const g = useGraficos();
  const [resaltado, setResaltado] = useState<number | null>(null);

  if (items.length === 0) {
    return (
      <div className={compartido.vacio}>
        <span>{vacio}</span>
      </div>
    );
  }

  const paleta = [g.principal, g.turquesa, g.ambar, g.pizarra, "#b4533a", "#5f7d4e"];
  const valorDe = (p: ProductoVendido) => (medida === "ventas" ? p.ventas : p.cantidad);
  const formatoValor = (v: number) => (medida === "ventas" ? moneda(v) : `${numero(v)} ${v === 1 ? "unidad" : "unidades"}`);
  const total = items.reduce((s, p) => s + valorDe(p), 0);
  const maximo = Math.max(...items.map(valorDe), 1);
  const datos = items.map((p, i) => ({
    nombre: p.nombre,
    valor: valorDe(p),
    fill: paleta[i % paleta.length],
    cantidad: p.cantidad,
    ventas: p.ventas,
    parte: total ? (valorDe(p) / total) * 100 : 0,
  }));

  const resumen = datos.map((d) => `${d.nombre} ${porcentaje(d.parte)}`).join(", ");
  // En los anillos, el primer plato debe quedar afuera (recharts dibuja el primero adentro).
  const anillos = [...datos].reverse();
  const original = (i: number) => datos.length - 1 - i;
  const atenuado = (i: number) => (resaltado !== null && resaltado !== i ? 0.35 : 1);

  return (
    <div className={styles.contenedor}>
      <div
        className={styles.grafico}
        style={{ width: TAMANO, height: TAMANO }}
        role="img"
        aria-label={`Platos ${medida === "ventas" ? "por ventas" : "por unidades"}: ${resumen}`}
      >
        <ResponsiveContainer width="100%" height="100%">
          {variante === "donut" ? (
            <PieChart>
              <Pie
                data={datos}
                dataKey="valor"
                nameKey="nombre"
                innerRadius={64}
                outerRadius={92}
                paddingAngle={datos.length > 1 ? 3 : 0}
                cornerRadius={5}
                stroke="none"
                animationDuration={700}
                onMouseEnter={(_, i) => setResaltado(i)}
                onMouseLeave={() => setResaltado(null)}
              >
                {datos.map((d, i) => (
                  <Cell key={d.nombre} fill={d.fill} fillOpacity={atenuado(i)} />
                ))}
              </Pie>
              <Tooltip
                {...g.tooltip}
                formatter={(v: number, _n: string, p: { payload?: { nombre: string } }) => [formatoValor(v), p.payload?.nombre ?? ""]}
              />
            </PieChart>
          ) : (
            <RadialBarChart
              data={anillos}
              innerRadius="28%"
              outerRadius="100%"
              barSize={Math.max(8, Math.min(18, 70 / datos.length))}
              startAngle={90}
              endAngle={-270}
            >
              <PolarAngleAxis type="number" domain={[0, maximo]} tick={false} />
              <RadialBar
                dataKey="valor"
                background={{ fill: g.grilla }}
                cornerRadius={8}
                animationDuration={700}
                onMouseEnter={(_, i) => setResaltado(original(i))}
                onMouseLeave={() => setResaltado(null)}
              >
                {anillos.map((d, i) => (
                  <Cell key={d.nombre} fill={d.fill} fillOpacity={atenuado(original(i))} />
                ))}
              </RadialBar>
              <Tooltip
                {...g.tooltip}
                formatter={(v: number, _n: string, p: { payload?: { nombre: string } }) => [formatoValor(v), p.payload?.nombre ?? ""]}
              />
            </RadialBarChart>
          )}
        </ResponsiveContainer>

        {variante === "donut" && (
          <div className={styles.centro} aria-hidden="true">
            <span className={styles.centroValor}>{medida === "ventas" ? moneda(total) : numero(total)}</span>
            <span className={styles.centroEtiqueta}>{medida === "ventas" ? "vendido" : total === 1 ? "unidad" : "unidades"}</span>
          </div>
        )}
      </div>

      <ol className={styles.leyenda}>
        {datos.map((d, i) => (
          <li
            key={d.nombre}
            className={`${styles.fila} ${resaltado === i ? styles.filaActiva : ""}`}
            onMouseEnter={() => setResaltado(i)}
            onMouseLeave={() => setResaltado(null)}
          >
            <span className={styles.punto} style={{ background: d.fill }} aria-hidden="true" />
            <span className={styles.nombre} title={d.nombre}>
              {d.nombre}
            </span>
            <span className={styles.cifras}>
              <strong>{medida === "ventas" ? moneda(d.ventas) : numero(d.cantidad)}</strong>
              {medida === "unidades" && <span className={styles.unidad}> {d.cantidad === 1 ? "unidad" : "unidades"}</span>}
            </span>
            <span className={styles.detalle}>
              {medida === "ventas" ? `${numero(d.cantidad)} ${d.cantidad === 1 ? "unidad" : "unidades"}` : moneda(d.ventas)}
            </span>
            <span className={styles.parte}>{porcentaje(d.parte)}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}
